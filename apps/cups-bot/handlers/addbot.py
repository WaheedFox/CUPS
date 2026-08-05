"""Handler: /addbot

Guides the developer through registering a new Project.
Multi-step conversation: ask name → ask type → create project → return project_id.

State machine per user_id (in-memory, sufficient for Phase 1).
"""

from __future__ import annotations

from titan import Router

from cups.service import CUPSService
from cups.domain.project import ProductType

router = Router()

# In-memory conversation state: {user_id: {"step": str, "name": str}}
_pending: dict[int, dict] = {}

# Phase 1: only product types with a registered Entitlement catalog are offered.
# bot, mini-app, and game will be added when their docs/services/<product>/ENTITLEMENTS.md
# files are created and their catalogs registered with the EntitlementEngine.
_PRODUCT_CHOICES = {
    "1": ProductType.TITAN_FRAMEWORK,
}

_TYPE_MENU = (
    "ما نوع المشروع؟\n\n"
    "1 — titan-framework\n\n"
    "ℹ️ أنواع إضافية (bot, mini-app, game) ستُضاف في مراحل لاحقة."
)


def register(service: CUPSService) -> Router:

    @router.command("addbot")
    async def addbot_start(ctx) -> None:
        # Ensure account exists
        service.get_or_create_account(ctx.sender.id)
        _pending[ctx.sender.id] = {"step": "waiting_name"}
        await ctx.reply("ما اسم مشروعك؟\n\nأرسل /cancel للإلغاء.")

    @router.command("cancel")
    async def cancel(ctx) -> None:
        if ctx.sender.id in _pending:
            del _pending[ctx.sender.id]
            await ctx.reply("تم الإلغاء.")

    @router.on("message")
    async def addbot_conversation(ctx) -> None:
        state = _pending.get(ctx.sender.id)
        if state is None:
            return  # not in a conversation — let other handlers deal with it

        text = (ctx.text or "").strip()

        # Any command during conversation cancels it
        if text.startswith("/"):
            del _pending[ctx.sender.id]
            return

        if state["step"] == "waiting_name":
            if not text:
                await ctx.reply("يرجى إرسال اسم المشروع.")
                return
            state["name"] = text
            state["step"] = "waiting_type"
            await ctx.reply(_TYPE_MENU)

        elif state["step"] == "waiting_type":
            product = _PRODUCT_CHOICES.get(text)
            if product is None:
                await ctx.reply(f"يرجى اختيار رقم من 1 إلى 4.\n\n{_TYPE_MENU}")
                return

            # All good — register the project
            del _pending[ctx.sender.id]

            project = service.register_project(
                owner_id=ctx.sender.id,
                product=product,
                name=state["name"],
            )

            await ctx.reply(
                f"✅ تم تسجيل مشروعك بنجاح!\n\n"
                f"الاسم:    {project.name}\n"
                f"النوع:    {project.product.value}\n"
                f"المعرّف:  <code>{project.project_id}</code>\n\n"
                f"ضع هذا المعرّف في كودك:\n"
                f"<code>cups = CUPSGuard(api_key=\"...\", "
                f"project_id=\"{project.project_id}\")</code>\n\n"
                f"خطتك الحالية: Starter 🆓\n"
                f"أرسل /plan لعرض تفاصيل Entitlements.",
                parse_mode="HTML",
            )

    return router
