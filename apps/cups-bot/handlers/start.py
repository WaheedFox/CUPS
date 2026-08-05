"""Handler: /start

Creates or retrieves the Account for the Telegram user.
This is the entry point into CUPS — every user begins here.
"""

from __future__ import annotations

from titan import Router

from cups.service import CUPSService

router = Router()


def register(service: CUPSService) -> Router:
    """Return a Router with /start wired to the given service instance."""

    @router.command("start")
    async def start(ctx) -> None:
        account, created = service.get_or_create_account(
            account_id=ctx.sender.id,
            username=ctx.sender.username if hasattr(ctx.sender, "username") else None,
        )

        if created:
            await ctx.reply(
                "مرحباً بك في CUPS 👋\n\n"
                "أنا هنا لإدارة اشتراكاتك ومشاريعك.\n\n"
                "لتسجيل مشروعك الأول، أرسل /addbot\n"
                "لعرض خطتك الحالية، أرسل /plan"
            )
        else:
            await ctx.reply(
                f"أهلاً بعودتك.\n\n"
                f"حسابك نشط. أرسل /plan لعرض خطتك، أو /addbot لتسجيل مشروع جديد."
            )

    return router
