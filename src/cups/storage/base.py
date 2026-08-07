"""Repository interfaces for CUPS storage.

Every storage backend (SQLite, future Postgres, test doubles) implements these.
The rest of CUPS depends only on these abstractions — never on a concrete store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.account import Account
from ..domain.project import Project
from ..domain.referral import (
    Commission,
    ReferralAttribution,
    ReferralCode,
    SimulatedPayment,
)
from ..domain.subscription import Subscription


class AccountRepository(ABC):
    @abstractmethod
    def get(self, account_id: int) -> Account | None: ...

    @abstractmethod
    def create(self, account: Account) -> None: ...


class ProjectRepository(ABC):
    @abstractmethod
    def get(self, project_id: UUID) -> Project | None: ...

    @abstractmethod
    def get_by_owner(self, owner_id: int) -> list[Project]: ...

    @abstractmethod
    def create(self, project: Project) -> None: ...


class SubscriptionRepository(ABC):
    @abstractmethod
    def get(self, account_id: int, product: str) -> Subscription | None: ...

    @abstractmethod
    def create(self, subscription: Subscription) -> None: ...

    @abstractmethod
    def update(self, subscription: Subscription) -> None: ...


class ReferralCodeRepository(ABC):
    @abstractmethod
    def get(self, code: str) -> ReferralCode | None: ...

    @abstractmethod
    def create(self, referral_code: ReferralCode) -> None: ...


class ReferralAttributionRepository(ABC):
    @abstractmethod
    def get(self, attribution_id: str) -> ReferralAttribution | None: ...

    @abstractmethod
    def get_by_referred(self, account_id: int) -> ReferralAttribution | None: ...

    @abstractmethod
    def create(self, attribution: ReferralAttribution) -> None: ...

    @abstractmethod
    def update(self, attribution: ReferralAttribution) -> None: ...


class SimulatedPaymentRepository(ABC):
    @abstractmethod
    def get(self, payment_id: str) -> SimulatedPayment | None: ...

    @abstractmethod
    def create(self, payment: SimulatedPayment) -> None: ...

    @abstractmethod
    def update(self, payment: SimulatedPayment) -> None: ...


class CommissionRepository(ABC):
    @abstractmethod
    def get_by_payment(self, payment_id: str) -> Commission | None: ...

    @abstractmethod
    def get_by_referrer(self, account_id: int) -> list[Commission]: ...

    @abstractmethod
    def create(self, commission: Commission) -> None: ...

    @abstractmethod
    def update(self, commission: Commission) -> None: ...
