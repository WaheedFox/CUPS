# CUPS — Unified Subscription Platform

منصة الاشتراكات والـ Entitlements الموحَّدة لمنظومة المنتجات.

## نظرة عامة

CUPS تدير **Accounts، Projects، Subscriptions، Entitlements، وPlans** عبر منتجات متعددة.
الوثائق الكاملة في [`docs/DOCUMENTATION-MAP.md`](docs/DOCUMENTATION-MAP.md).

## القاعدة الجوهرية

> **Runtime MUST NEVER evaluate subscriptions directly.**
> **Runtime MUST consume resolved entitlements only.**

## هيكل المشروع

```
src/cups/          ← CUPS Platform (Python package — لا يعتمد على Titan)
  domain/          ← Account, Project, Subscription, Entitlement
  catalog/         ← تعريفات Entitlements لكل منتج (titan-framework, cups-bot)
  engine/          ← Entitlement Resolution Engine
  storage/         ← SQLiteStore + Repository abstractions
  service.py       ← CUPSService — الواجهة الرئيسية
  api/runtime.py   ← FastAPI Runtime API

apps/cups-bot/     ← CUPS Bot (مبني فوق Titan — dogfooding)
  handlers/        ← /start, /addbot, /plan
  main.py          ← Entry point

docs/              ← الوثائق والمعمار والقرارات
tests/             ← 37 اختباراً (domain + engine + api)
```

## تشغيل الـ Runtime API

```bash
# تثبيت الحزمة (مرة واحدة)
pip install -e ".[dev]"

# تشغيل الـ API
uvicorn cups.api.runtime:app --host 0.0.0.0 --port 8000
```

Endpoint: `POST /entitlements/check`
```json
{ "account_id": 123, "project_id": "uuid-here", "entitlement": "atlas_access" }
→ { "granted": false, "value": false }
```

## تشغيل CUPS Bot

```bash
# متطلب: ضبط BOT_TOKEN في Replit Secrets
PYTHONPATH=src python apps/cups-bot/main.py
```

## تشغيل الاختبارات

```bash
pytest
# أو بتفاصيل:
pytest -v
```

## المتطلبات البيئية

| المتغير | المصدر | الاستخدام |
|---|---|---|
| `BOT_TOKEN` | Replit Secrets | Telegram bot token لـ CUPS Bot |

## Phase الحالية

**Phase 1** — الهيكل الأساسي مكتمل:
- Account (ينشأ عند /start)
- Project (يُسجَّل عبر /addbot، يُعطي project_id)
- Subscription (Starter تلقائية، بلا دفع)
- Entitlement Resolution (Subscription → Resolved Entitlements)
- Runtime API (POST /entitlements/check)
- CUPS Bot (/start, /addbot, /plan)

**Phase التالية:** Phase 2 — Subscription Engine كامل (trial → active → grace → frozen → expired)

## User Preferences

- Full UUID4 للـ project_id (لا اختصار)
- SQLite مع Repository abstraction للتخزين
- CUPS Platform لا يعتمد على Titan — Titan مستهلك مستقبلي فقط
- CUPS Bot يستخدم Titan كـ framework (dogfooding)
- لا تغيير في بنية الوثائق (PHILOSOPHY, DOMAIN, ARCHITECTURE) إلا بقرار معماري صريح
