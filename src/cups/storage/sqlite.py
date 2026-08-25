"""SQLite-backed storage for CUPS Phase 1.

Uses Python's built-in sqlite3 — no external dependencies.

Connection strategy:
  A single persistent connection per SQLiteStore instance is shared across all
  repositories. This is required for :memory: databases (each new connection to
  :memory: creates a separate, empty database). It also works correctly for
  file-based databases in single-process deployments (Phase 1).

Thread safety: check_same_thread=False is set. The CUPS API and bot are
single-threaded workers; this is acceptable for Phase 1.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from ..domain.account import Account
from ..domain.project import Project, ProductType
from ..domain.resources import Consumption, Quota, Reservation
from ..domain.referral import (
    Commission,
    CommissionStatus,
    PaymentStatus,
    ReferralAttribution,
    ReferralCode,
    SimulatedPayment,
)
from ..domain.subscription import PlanName, Subscription, SubscriptionStatus
from .base import (
    AccountRepository,
    CommissionRepository,
    ProjectRepository,
    ReferralAttributionRepository,
    ReferralCodeRepository,
    SimulatedPaymentRepository,
    SubscriptionRepository,
)

# ─── Schema ──────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id  INTEGER PRIMARY KEY,
    username    TEXT,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS projects (
    project_id    TEXT PRIMARY KEY,
    owner_id      INTEGER NOT NULL,
    product       TEXT NOT NULL,
    name          TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (owner_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,
    account_id      INTEGER NOT NULL,
    product         TEXT NOT NULL,
    plan            TEXT NOT NULL,
    status          TEXT NOT NULL,
    period          TEXT NOT NULL DEFAULT 'monthly',
    started_at      TEXT NOT NULL,
    expires_at      TEXT,
    trial_ends_at   TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_account_product
    ON subscriptions (account_id, product);

CREATE TABLE IF NOT EXISTS referral_codes (
    code             TEXT PRIMARY KEY,
    owner_account_id INTEGER NOT NULL,
    created_at       TEXT NOT NULL,
    active           INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (owner_account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS referral_attributions (
    attribution_id          TEXT PRIMARY KEY,
    referrer_account_id     INTEGER NOT NULL,
    referred_account_id     INTEGER NOT NULL UNIQUE,
    referral_code           TEXT NOT NULL,
    attributed_at           TEXT NOT NULL,
    first_eligible_payment_at TEXT,
    FOREIGN KEY (referrer_account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (referred_account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (referral_code) REFERENCES referral_codes(code),
    CHECK (referrer_account_id <> referred_account_id)
);

CREATE TABLE IF NOT EXISTS simulated_payments (
    payment_id      TEXT PRIMARY KEY,
    account_id      INTEGER NOT NULL,
    product         TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    amount_minor    INTEGER NOT NULL,
    currency        TEXT NOT NULL,
    status          TEXT NOT NULL,
    paid_at         TEXT NOT NULL,
    refunded_at     TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS commissions (
    commission_id          TEXT PRIMARY KEY,
    attribution_id         TEXT NOT NULL,
    payment_id             TEXT NOT NULL UNIQUE,
    gross_amount_minor     INTEGER NOT NULL,
    rate_bps               INTEGER NOT NULL,
    commission_amount_minor INTEGER NOT NULL,
    status                 TEXT NOT NULL,
    created_at             TEXT NOT NULL,
    reversed_at            TEXT,
    FOREIGN KEY (attribution_id) REFERENCES referral_attributions(attribution_id),
    FOREIGN KEY (payment_id) REFERENCES simulated_payments(payment_id)
);

CREATE TABLE IF NOT EXISTS reservations (
    reservation_id  TEXT PRIMARY KEY,
    account_id      INTEGER NOT NULL,
    project_id      TEXT NOT NULL,
    resource_key    TEXT NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    status          TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE (account_id, project_id, resource_key, idempotency_key),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS consumptions (
    consumption_id  TEXT PRIMARY KEY,
    usage_record_id TEXT NOT NULL UNIQUE,
    account_id      INTEGER NOT NULL,
    project_id      TEXT NOT NULL,
    resource_key    TEXT NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity >= 0),
    reservation_id  TEXT,
    source_event_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    occurred_at     TEXT NOT NULL,
    committed_at    TEXT NOT NULL,
    UNIQUE (account_id, project_id, resource_key, idempotency_key),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id)
);
"""

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_dt(val: str | None) -> datetime | None:
    return datetime.fromisoformat(val) if val else None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ─── Store ────────────────────────────────────────────────────────────────────

class SQLiteStore:
    """Holds a single SQLite connection shared across all repositories.

    This is required so that :memory: databases work correctly in tests — each
    new sqlite3.connect(':memory:') would create a separate empty database.
    """

    def __init__(self, db_path: str | Path = "cups.db") -> None:
        self._conn = sqlite3.connect(
            str(db_path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @property
    def accounts(self) -> "SQLiteAccountRepo":
        return SQLiteAccountRepo(self._conn)

    @property
    def projects(self) -> "SQLiteProjectRepo":
        return SQLiteProjectRepo(self._conn)

    @property
    def subscriptions(self) -> "SQLiteSubscriptionRepo":
        return SQLiteSubscriptionRepo(self._conn)

    @property
    def referral_codes(self) -> "SQLiteReferralCodeRepo":
        return SQLiteReferralCodeRepo(self._conn)

    @property
    def referral_attributions(self) -> "SQLiteReferralAttributionRepo":
        return SQLiteReferralAttributionRepo(self._conn)

    @property
    def simulated_payments(self) -> "SQLiteSimulatedPaymentRepo":
        return SQLiteSimulatedPaymentRepo(self._conn)

    @property
    def commissions(self) -> "SQLiteCommissionRepo":
        return SQLiteCommissionRepo(self._conn)

    def close(self) -> None:
        self._conn.close()

    def get_quota(
        self, account_id: int, project_id: UUID, resource_key: str,
        limit: int | None,
    ) -> Quota:
        project = str(project_id)
        used = self._conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM consumptions "
            "WHERE account_id = ? AND project_id = ? AND resource_key = ?",
            (account_id, project, resource_key),
        ).fetchone()[0]
        reserved = self._conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
            "WHERE account_id = ? AND project_id = ? AND resource_key = ? "
            "AND status = 'active' AND expires_at > ?",
            (account_id, project, resource_key, datetime.utcnow().isoformat()),
        ).fetchone()[0]
        remaining = None if limit is None else max(limit - used - reserved, 0)
        return Quota(account_id, project_id, resource_key, limit, used, reserved, remaining)

    def create_reservation(
        self, reservation: Reservation, limit: int | None,
    ) -> Reservation:
        """Create a reservation under an immediate SQLite transaction."""
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self._conn.execute(
                "SELECT * FROM reservations WHERE account_id = ? AND project_id = ? "
                "AND resource_key = ? AND idempotency_key = ?",
                (reservation.account_id, str(reservation.project_id),
                 reservation.resource_key, reservation.idempotency_key),
            ).fetchone()
            if existing:
                if int(existing["quantity"]) != reservation.quantity:
                    raise ValueError("IDEMPOTENCY_CONFLICT")
                self._conn.commit()
                return _row_to_reservation(existing)
            now = datetime.utcnow().isoformat()
            self._conn.execute(
                "UPDATE reservations SET status = 'expired' "
                "WHERE status = 'active' AND expires_at <= ?", (now,)
            )
            used = self._conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM consumptions "
                "WHERE account_id = ? AND project_id = ? AND resource_key = ?",
                (reservation.account_id, str(reservation.project_id),
                 reservation.resource_key),
            ).fetchone()[0]
            reserved = self._conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
                "WHERE account_id = ? AND project_id = ? AND resource_key = ? "
                "AND status = 'active'",
                (reservation.account_id, str(reservation.project_id),
                 reservation.resource_key),
            ).fetchone()[0]
            if limit is not None and used + reserved + reservation.quantity > limit:
                raise ValueError("QUOTA_EXCEEDED")
            self._conn.execute(
                "INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (reservation.reservation_id, reservation.account_id,
                 str(reservation.project_id), reservation.resource_key,
                 reservation.quantity, reservation.status,
                 reservation.expires_at.isoformat(), reservation.idempotency_key,
                 now),
            )
            self._conn.commit()
            return reservation
        except Exception:
            self._conn.rollback()
            raise

    def create_consumption(
        self, consumption: Consumption, limit: int | None,
    ) -> Consumption:
        """Atomically deduplicate, validate, and commit resource consumption."""
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            key = (consumption.account_id, str(consumption.project_id),
                   consumption.resource_key, consumption.idempotency_key)
            existing = self._conn.execute(
                "SELECT * FROM consumptions WHERE account_id = ? AND project_id = ? "
                "AND resource_key = ? AND idempotency_key = ?", key,
            ).fetchone()
            if existing:
                same = (
                    int(existing["quantity"]) == consumption.quantity
                    and existing["reservation_id"] == consumption.reservation_id
                    and existing["source_event_id"] == consumption.source_event_id
                )
                if not same:
                    raise ValueError("IDEMPOTENCY_CONFLICT")
                self._conn.commit()
                return _row_to_consumption(existing, limit, True, self._conn)

            now = datetime.utcnow().isoformat()
            self._conn.execute(
                "UPDATE reservations SET status = 'expired' "
                "WHERE status = 'active' AND expires_at <= ?", (now,)
            )
            if consumption.reservation_id:
                reservation = self._conn.execute(
                    "SELECT * FROM reservations WHERE reservation_id = ?",
                    (consumption.reservation_id,),
                ).fetchone()
                if reservation is None:
                    raise ValueError("RESERVATION_NOT_FOUND")
                if (
                    reservation["account_id"] != consumption.account_id
                    or reservation["project_id"] != str(consumption.project_id)
                    or reservation["resource_key"] != consumption.resource_key
                ):
                    raise ValueError("RESERVATION_NOT_FOUND")
                if reservation["status"] != "active":
                    raise ValueError("RESERVATION_EXPIRED")
                if consumption.quantity > int(reservation["quantity"]):
                    raise ValueError("CONSUMPTION_EXCEEDS_RESERVATION")
            used = self._conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM consumptions "
                "WHERE account_id = ? AND project_id = ? AND resource_key = ?",
                (consumption.account_id, str(consumption.project_id),
                 consumption.resource_key),
            ).fetchone()[0]
            reserved = self._conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
                "WHERE account_id = ? AND project_id = ? AND resource_key = ? "
                "AND status = 'active'",
                (consumption.account_id, str(consumption.project_id),
                 consumption.resource_key),
            ).fetchone()[0]
            if (
                not consumption.reservation_id
                and limit is not None
                and used + reserved + consumption.quantity > limit
            ):
                raise ValueError("QUOTA_EXCEEDED")
            self._conn.execute(
                "INSERT INTO consumptions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (consumption.consumption_id, consumption.usage_record_id,
                 consumption.account_id, str(consumption.project_id),
                 consumption.resource_key, consumption.quantity,
                 consumption.reservation_id, consumption.source_event_id,
                 consumption.idempotency_key, consumption.occurred_at.isoformat(),
                 consumption.committed_at.isoformat()),
            )
            if consumption.reservation_id:
                self._conn.execute(
                    "UPDATE reservations SET status = 'committed' "
                    "WHERE reservation_id = ?", (consumption.reservation_id,)
                )
            self._conn.commit()
            return _row_to_consumption(
                self._conn.execute(
                    "SELECT * FROM consumptions WHERE consumption_id = ?",
                    (consumption.consumption_id,),
                ).fetchone(), limit, False, self._conn,
            )
        except Exception:
            self._conn.rollback()
            raise


# ─── Account Repository ───────────────────────────────────────────────────────

class SQLiteAccountRepo(AccountRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, account_id: int) -> Account | None:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        if row is None:
            return None
        return Account(
            account_id=row["account_id"],
            username=row["username"],
            created_at=datetime.fromisoformat(row["created_at"]),
            status=row["status"],
        )

    def create(self, account: Account) -> None:
        self._conn.execute(
            "INSERT INTO accounts (account_id, username, created_at, status) "
            "VALUES (?, ?, ?, ?)",
            (account.account_id, account.username,
             account.created_at.isoformat(), account.status),
        )
        self._conn.commit()


# ─── Project Repository ───────────────────────────────────────────────────────

class SQLiteProjectRepo(ProjectRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, project_id: UUID) -> Project | None:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE project_id = ?", (str(project_id),)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_project(row)

    def get_by_owner(self, owner_id: int) -> list[Project]:
        rows = self._conn.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY registered_at",
            (owner_id,),
        ).fetchall()
        return [self._row_to_project(row) for row in rows]

    def create(self, project: Project) -> None:
        self._conn.execute(
            "INSERT INTO projects "
            "(project_id, owner_id, product, name, registered_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(project.project_id), project.owner_id, project.product.value,
             project.name, project.registered_at.isoformat(), project.status),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> Project:
        return Project(
            project_id=UUID(row["project_id"]),
            owner_id=row["owner_id"],
            product=ProductType(row["product"]),
            name=row["name"],
            registered_at=datetime.fromisoformat(row["registered_at"]),
            status=row["status"],
        )


# ─── Subscription Repository ──────────────────────────────────────────────────

class SQLiteSubscriptionRepo(SubscriptionRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, account_id: int, product: str) -> Subscription | None:
        row = self._conn.execute(
            "SELECT * FROM subscriptions WHERE account_id = ? AND product = ?",
            (account_id, product),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_sub(row)

    def create(self, subscription: Subscription) -> None:
        self._conn.execute(
            "INSERT INTO subscriptions "
            "(subscription_id, account_id, product, plan, status, period, "
            "started_at, expires_at, trial_ends_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (subscription.subscription_id, subscription.account_id,
             subscription.product, subscription.plan.value,
             subscription.status.value, subscription.period,
             subscription.started_at.isoformat(),
             _iso(subscription.expires_at), _iso(subscription.trial_ends_at)),
        )
        self._conn.commit()

    def update(self, subscription: Subscription) -> None:
        self._conn.execute(
            "UPDATE subscriptions SET plan = ?, status = ?, period = ?, "
            "expires_at = ?, trial_ends_at = ? "
            "WHERE subscription_id = ?",
            (subscription.plan.value, subscription.status.value, subscription.period,
             _iso(subscription.expires_at), _iso(subscription.trial_ends_at),
             subscription.subscription_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_sub(row: sqlite3.Row) -> Subscription:
        return Subscription(
            subscription_id=row["subscription_id"],
            account_id=row["account_id"],
            product=row["product"],
            plan=PlanName(row["plan"]),
            status=SubscriptionStatus(row["status"]),
            period=row["period"],
            started_at=datetime.fromisoformat(row["started_at"]),
            expires_at=_parse_dt(row["expires_at"]),
            trial_ends_at=_parse_dt(row["trial_ends_at"]),
        )


class SQLiteReferralCodeRepo(ReferralCodeRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, code: str) -> ReferralCode | None:
        row = self._conn.execute(
            "SELECT * FROM referral_codes WHERE code = ?", (code,)
        ).fetchone()
        if row is None:
            return None
        return ReferralCode(
            code=row["code"],
            owner_account_id=row["owner_account_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            active=bool(row["active"]),
        )

    def create(self, referral_code: ReferralCode) -> None:
        self._conn.execute(
            "INSERT INTO referral_codes (code, owner_account_id, created_at, active) "
            "VALUES (?, ?, ?, ?)",
            (
                referral_code.code,
                referral_code.owner_account_id,
                referral_code.created_at.isoformat(),
                int(referral_code.active),
            ),
        )
        self._conn.commit()


class SQLiteReferralAttributionRepo(ReferralAttributionRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, attribution_id: str) -> ReferralAttribution | None:
        row = self._conn.execute(
            "SELECT * FROM referral_attributions WHERE attribution_id = ?",
            (attribution_id,),
        ).fetchone()
        return self._row_to_attribution(row) if row else None

    def get_by_referred(self, account_id: int) -> ReferralAttribution | None:
        row = self._conn.execute(
            "SELECT * FROM referral_attributions WHERE referred_account_id = ?",
            (account_id,),
        ).fetchone()
        return self._row_to_attribution(row) if row else None

    def create(self, attribution: ReferralAttribution) -> None:
        self._conn.execute(
            "INSERT INTO referral_attributions "
            "(attribution_id, referrer_account_id, referred_account_id, "
            "referral_code, attributed_at, first_eligible_payment_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                attribution.attribution_id,
                attribution.referrer_account_id,
                attribution.referred_account_id,
                attribution.referral_code,
                attribution.attributed_at.isoformat(),
                _iso(attribution.first_eligible_payment_at),
            ),
        )
        self._conn.commit()

    def update(self, attribution: ReferralAttribution) -> None:
        self._conn.execute(
            "UPDATE referral_attributions SET first_eligible_payment_at = ? "
            "WHERE attribution_id = ?",
            (
                _iso(attribution.first_eligible_payment_at),
                attribution.attribution_id,
            ),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_attribution(row: sqlite3.Row) -> ReferralAttribution:
        return ReferralAttribution(
            attribution_id=row["attribution_id"],
            referrer_account_id=row["referrer_account_id"],
            referred_account_id=row["referred_account_id"],
            referral_code=row["referral_code"],
            attributed_at=datetime.fromisoformat(row["attributed_at"]),
            first_eligible_payment_at=_parse_dt(
                row["first_eligible_payment_at"]
            ),
        )


class SQLiteSimulatedPaymentRepo(SimulatedPaymentRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, payment_id: str) -> SimulatedPayment | None:
        row = self._conn.execute(
            "SELECT * FROM simulated_payments WHERE payment_id = ?",
            (payment_id,),
        ).fetchone()
        return self._row_to_payment(row) if row else None

    def create(self, payment: SimulatedPayment) -> None:
        self._conn.execute(
            "INSERT INTO simulated_payments "
            "(payment_id, account_id, product, subscription_id, amount_minor, "
            "currency, status, paid_at, refunded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payment.payment_id,
                payment.account_id,
                payment.product,
                payment.subscription_id,
                payment.amount_minor,
                payment.currency,
                payment.status.value,
                payment.paid_at.isoformat(),
                _iso(payment.refunded_at),
            ),
        )
        self._conn.commit()

    def update(self, payment: SimulatedPayment) -> None:
        self._conn.execute(
            "UPDATE simulated_payments SET status = ?, refunded_at = ? "
            "WHERE payment_id = ?",
            (
                payment.status.value,
                _iso(payment.refunded_at),
                payment.payment_id,
            ),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_payment(row: sqlite3.Row) -> SimulatedPayment:
        return SimulatedPayment(
            payment_id=row["payment_id"],
            account_id=row["account_id"],
            product=row["product"],
            subscription_id=row["subscription_id"],
            amount_minor=row["amount_minor"],
            currency=row["currency"],
            status=PaymentStatus(row["status"]),
            paid_at=datetime.fromisoformat(row["paid_at"]),
            refunded_at=_parse_dt(row["refunded_at"]),
        )


class SQLiteCommissionRepo(CommissionRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_payment(self, payment_id: str) -> Commission | None:
        row = self._conn.execute(
            "SELECT * FROM commissions WHERE payment_id = ?", (payment_id,)
        ).fetchone()
        return self._row_to_commission(row) if row else None

    def get_by_referrer(self, account_id: int) -> list[Commission]:
        rows = self._conn.execute(
            "SELECT c.* FROM commissions c "
            "JOIN referral_attributions a ON a.attribution_id = c.attribution_id "
            "WHERE a.referrer_account_id = ? ORDER BY c.created_at",
            (account_id,),
        ).fetchall()
        return [self._row_to_commission(row) for row in rows]

    def create(self, commission: Commission) -> None:
        self._conn.execute(
            "INSERT INTO commissions "
            "(commission_id, attribution_id, payment_id, gross_amount_minor, "
            "rate_bps, commission_amount_minor, status, created_at, reversed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                commission.commission_id,
                commission.attribution_id,
                commission.payment_id,
                commission.gross_amount_minor,
                commission.rate_bps,
                commission.commission_amount_minor,
                commission.status.value,
                commission.created_at.isoformat(),
                _iso(commission.reversed_at),
            ),
        )
        self._conn.commit()

    def update(self, commission: Commission) -> None:
        self._conn.execute(
            "UPDATE commissions SET status = ?, reversed_at = ? "
            "WHERE commission_id = ?",
            (
                commission.status.value,
                _iso(commission.reversed_at),
                commission.commission_id,
            ),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_commission(row: sqlite3.Row) -> Commission:
        return Commission(
            commission_id=row["commission_id"],
            attribution_id=row["attribution_id"],
            payment_id=row["payment_id"],
            gross_amount_minor=row["gross_amount_minor"],
            rate_bps=row["rate_bps"],
            commission_amount_minor=row["commission_amount_minor"],
            status=CommissionStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            reversed_at=_parse_dt(row["reversed_at"]),
        )


def _row_to_reservation(row: sqlite3.Row) -> Reservation:
    return Reservation(
        reservation_id=row["reservation_id"],
        account_id=row["account_id"],
        project_id=UUID(row["project_id"]),
        resource_key=row["resource_key"],
        quantity=row["quantity"],
        status=row["status"],
        expires_at=datetime.fromisoformat(row["expires_at"]),
        idempotency_key=row["idempotency_key"],
    )


def _row_to_consumption(
    row: sqlite3.Row,
    limit: int | None,
    already_committed: bool,
    conn: sqlite3.Connection,
) -> Consumption:
    used = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM consumptions "
        "WHERE account_id = ? AND project_id = ? AND resource_key = ?",
        (row["account_id"], row["project_id"], row["resource_key"]),
    ).fetchone()[0]
    reserved = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM reservations "
        "WHERE account_id = ? AND project_id = ? AND resource_key = ? "
        "AND status = 'active' AND expires_at > ?",
        (row["account_id"], row["project_id"], row["resource_key"],
         datetime.utcnow().isoformat()),
    ).fetchone()[0]
    remaining = None if limit is None else max(limit - used - reserved, 0)
    return Consumption(
        consumption_id=row["consumption_id"],
        usage_record_id=row["usage_record_id"],
        account_id=row["account_id"],
        project_id=UUID(row["project_id"]),
        resource_key=row["resource_key"],
        quantity=row["quantity"],
        reservation_id=row["reservation_id"],
        source_event_id=row["source_event_id"],
        idempotency_key=row["idempotency_key"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        committed_at=datetime.fromisoformat(row["committed_at"]),
        remaining=remaining,
        already_committed=already_committed,
    )
