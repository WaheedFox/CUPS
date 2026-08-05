"""Repository interfaces for CUPS storage.

Every storage backend (SQLite, future Postgres, test doubles) implements these.
The rest of CUPS depends only on these abstractions — never on a concrete store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.account import Account
from ..domain.project import Project
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
