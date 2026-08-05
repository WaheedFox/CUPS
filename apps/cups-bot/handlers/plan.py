"""Handler: /plan

Displays the account's current plan and Resolved Entitlements
for each registered product.

Shows Entitlements — not subscription state. Runtime sees exactly what this shows.
"""

from __future__ import annotations

from titan import Router

from cups.service import CUPSService
from cups.domain.project import ProductType
from cups.domain.subscription import PlanName

router = Router()

# Human-readable plan labels
_PLAN_LABELS: dict[PlanName, str] = {
    PlanName.STARTER: "Starter 🆓",
    PlanName.PLUS: "Plus ✨ ($4.99/شهر)",
    PlanName.CORE: "Core ⚡ ($7.99/شهر)",
    PlanName.ULTRA: "Ultra 🚀 ($14.99/شهر)",
}


def register(service: CUPSService) -> Router:

    @router.command("plan")
    async def plan(ctx) -> None:
        account = service.get_account(ctx.sender.id)
        if account is None:
            await ctx.reply("لم أجد حسابك. أرسل /start أولاً.")
            return

        projects = service.get_projects(ctx.sender.id)
        if not projects:
            await ctx.reply(
                "لا يوجد لديك مشاريع مسجَّلة بعد.\n"
                "أرسل /addbot لتسجيل مشروعك الأول."
            )
            return

        lines: list[str] = ["<b>خطتك الحالية</b>\n"]

        # Show per-product summary (one subscription per product)
        seen_products: set[str] = set()
        for project in projects:
            product_key = project.product.value
            if product_key in seen_products:
                continue
            seen_products.add(product_key)

            sub = service.get_subscription(ctx.sender.id, product_key)
            plan_label = _PLAN_LABELS.get(sub.plan, sub.plan.value) if sub else "Starter 🆓"
            resolved = service.get_resolved_entitlements(ctx.sender.id, product_key)

            lines.append(f"📦 <b>{product_key}</b>  —  {plan_label}")
            lines.append(_format_entitlements(resolved))
            lines.append("")

        lines.append(f"مشاريعك ({len(projects)}):")
        for p in projects:
            lines.append(f"  • {p.name}  <code>{p.project_id}</code>")

        await ctx.reply("\n".join(lines), parse_mode="HTML")

    return router


def _format_entitlements(resolved: dict) -> str:
    """Format Resolved Entitlements as a readable list."""
    parts = []
    for key, value in resolved.items():
        if isinstance(value, bool):
            icon = "✅" if value else "❌"
            parts.append(f"  {icon} {key}")
        elif isinstance(value, int):
            parts.append(f"  📊 {key}: {value}")
        else:
            parts.append(f"  🔧 {key}: {value}")
    return "\n".join(parts)
