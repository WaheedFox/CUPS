"""Account — the fundamental identity in CUPS.

account_id = Telegram user_id.
No alternative identity in this phase. CUPS operates inside Telegram only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Account:
    """Represents a real person inside Telegram.

    Created automatically on first interaction with CUPS Bot.
    Never deleted — only closed or suspended.
    """

    account_id: int  # Telegram user_id — the one true identity
    username: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"  # active | suspended
