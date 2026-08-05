# CUPS — Unified Subscription Platform

> منصة الاشتراكات والـ Entitlements الموحَّدة لمنظومة المنتجات.

CUPS تدير **Accounts، Projects، Subscriptions، Entitlements، وPlans** عبر منتجات متعددة — Titan bots، Mini Apps، games، وما سيأتي لاحقاً.

---

## الوثائق

ابدأ من [`docs/DOCUMENTATION-MAP.md`](docs/DOCUMENTATION-MAP.md) — خريطة القراءة الكاملة.

| الوثيقة | المحتوى |
|---|---|
| [`docs/PRODUCT_PHILOSOPHY.md`](docs/PRODUCT_PHILOSOPHY.md) | لماذا يوجد CUPS |
| [`docs/DOMAIN.md`](docs/DOMAIN.md) | تعريفات الكيانات الرسمية |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | المعمار، Decision Flow، Consistency Model |
| [`docs/PLANS.md`](docs/PLANS.md) | الخطط والأسعار |
| [`docs/services/`](docs/services/) | Entitlements لكل منتج |

---

## هيكل المستودع

```
src/cups/          ← CUPS Platform (الكود الأساسي)
apps/cups-bot/     ← CUPS Bot Application (الباب الأمامي)
docs/              ← الوثائق والمعمار والقرارات
tests/             ← الاختبارات
```

---

## القاعدة الجوهرية

> **Runtime MUST NEVER evaluate subscriptions directly.**
> **Runtime MUST consume resolved entitlements only.**

---

## المؤلف

Waheed
