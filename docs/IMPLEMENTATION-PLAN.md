# CUPS — Implementation Plan

> هذه ليست وثيقة فلسفية.
> هي ترتيب البناء.
>
> كل Phase يُنتج شيئاً يعمل فعلاً — لا مجرد كود جاهز للـ Phase التالية.

---

## المبدأ الذي يحكم هذا الترتيب

**أبنِ أضيق شيء يعمل نهاية لنهاية أولاً.**

Phase 1 يجب أن تُنتج نظاماً حقيقياً — حتى لو كان Starter فقط، بلا دفع، بلا Atlas.
كل Phase بعدها توسّع على شيء يعمل، لا تُكمل شيئاً مكسوراً.

**ترتيب الـ Phases مبني على قاعدة واحدة:**
الـ SDK يُبنى بعد أن يصبح الـ Runtime نهائياً — لا قبله.
`cups.require()` يُكتب مرة واحدة، لا مرة ثم تُعاد كتابتها بعد إضافة Trial وGrace وFrozen.

---

## Phase 0 — فصل المستودع

**الهدف:** CUPS يبدأ تاريخه المستقل قبل أول سطر إنتاجي.

### ما يحدث

- إنشاء مستودع مستقل: `cups` (أو `cups-platform` — يُحدَّد)
- نقل كل وثائق CUPS من `products/cups/` إلى الجذر الجديد
- إعداد الهيكل الأساسي للمشروع (Python package، CI skeleton، README يشير لـ DOCUMENTATION-MAP)

### لماذا قبل Phase 1 وليس بعده

إذا بدأ التنفيذ داخل Titan repo:
- كل Commit يصبح جزءاً من تاريخ Titan لا CUPS
- الـ merge conflicts تبدأ من اليوم الأول
- CUPS يصبح عملياً "مجلداً داخل Titan" — وهذا ضد فلسفته كـ Platform مستقل

CUPS منظومة تخدم Titan وغيره. مستودعها يعكس هذا من الـ commit الأول.

### كيف تعرف أنها انتهت
```
git clone cups-repo
cd cups
ls
→ docs/  src/  README.md  (لا titan في أي مكان)
```

---

## Phase 1 — الهيكل الأساسي

**الهدف:** نظام يعرف من أنت وما تملك.

### ما يُبنى

**CUPS Core (Python Service):**
- `Account` — ينشأ عند أول `/start`
- `Project` — يُسجَّل عبر `/addbot`، يُعطي `project_id`
- `Subscription` — Starter فقط، تلقائية، بلا دفع
- `Entitlement Resolution` — يحوّل Subscription → Resolved Entitlements
- `Runtime API` — endpoint واحد:
  ```
  POST /entitlements/check
  { account_id, project_id, entitlement }
  → { granted: true/false, value: ... }
  ```

**CUPS Bot (Telegram Bot):**
- `/start` — ينشئ Account أو يسترجعه
- `/addbot` — يسجّل Project ويُعطي `project_id`
- `/plan` — يعرض الخطة الحالية والـ Entitlements

### ما لا يُبنى في هذه المرحلة
- لا دفع
- لا Trial
- لا Atlas أو أي Entitlement مدفوع فعلي
- لا فريق

### كيف تعرف أنها انتهت
```
مطور يفتح CUPS Bot
       ↓ /addbot
       ↓ يحصل على project_id
       ↓ يضعه في كوده
       ↓ يستدعي /entitlements/check
       ↓ يحصل على { granted: false } لأي Entitlement مدفوع
       ↓ يحصل على { granted: true } لـ Entitlements الـ Starter
```

---

## Phase 2 — Subscription Engine

**الهدف:** الـ Runtime يصبح نهائياً — قبل أن يُبنى أي SDK عليه.

### ما يُبنى

**Subscription Lifecycle (كامل):**
```
trial → active → grace → frozen → expired → Starter
```
كل حالة موجودة، كل انتقال يعمل. لا Billing UI حقيقي بعد — الدفع يُحاكى داخلياً.

**Business Events (محاكاة):**
```python
# داخلياً فقط — لا مزوّد دفع خارجي بعد
cups.simulate_payment(account_id, plan="plus")  # → PaymentSucceeded
cups.simulate_expiry(account_id)                # → SubscriptionExpired
```

- `PaymentSucceeded` → Subscription تُفعَّل → Entitlement Resolution يُشغَّل
- `PaymentFailed` → grace period
- `SubscriptionExpired` → frozen → Starter
- `RefundIssued` → إعادة حساب فورية

**Entitlement Resolution (كامل):**
- يعمل على كل تغيير حالة
- Cache invalidation عند كل انتقال
- في حالة التعارض: CUPS Engine هو المرجع

**Trial Flow:**
- 3 أيام تُفتح تلقائياً
- آلية تمديد بناءً على الاستخدام
- الانتهاء بدون دفع → Starter تلقائياً

### ما لا يُبنى
- لا مزوّد دفع خارجي (Stripe / Telegram Stars — Phase 3)
- لا SDK بعد
- لا زر `/upgrade` حقيقي

### لماذا هذا قبل SDK

بعد هذه المرحلة، Runtime له حالات:
`trial`, `active`, `grace`, `frozen`, `expired`

الـ SDK الذي سيُبنى في Phase 3 سيتعامل مع **كل** هذه الحالات من اليوم الأول.
لو بُني SDK قبل هذا، كان سيُكتب على Runtime أبسط ثم يُعاد جزء منه بعد إضافة Grace وFrozen.

### كيف تعرف أنها انتهت
```
# محاكاة كاملة بدون Telegram Bot للدفع
cups.simulate_payment(account_id=123, plan="plus")
→ Entitlement Resolution يُشغَّل
→ atlas_access = true

cups.simulate_expiry(account_id=123)
→ grace period
→ بعد المدة: frozen
→ بعد المدة: Starter تلقائياً
→ atlas_access = false
```

---

## Phase 3 — titan-extension-cups

**الهدف:** أي مطور Titan يستطيع ربط بوته بـ CUPS في 5 دقائق — على Runtime نهائي.

### ما يُبنى

**`titan-extension-cups` (Python Package):**
```python
cups = CUPSGuard(api_key="...", project_id="abc123")
bot.middleware(cups.as_middleware())

@bot.command("export")
async def export_data(ctx):
    if not await cups.require(ctx, entitlement="data_export"):
        return
    # ... المنطق الفعلي
```

- `CUPSGuard.as_middleware()` — يُضيف Resolved Entitlements لكل ctx
- `cups.require(ctx, entitlement)` — يُوقف ويُبلّغ إذا لم يملك الحق
- `cups.check(ctx, entitlement)` — يُعيد `True/False` بدون إيقاف
- Cache محلي للـ Resolved Entitlements (TTL) — يُبطَل عند تغيير Subscription
- Fallback عند عدم وصول CUPS (fail-open أو fail-closed — قرار تشغيلي)

**ربط Billing حقيقي:**
- مزوّد دفع خارجي (Telegram Stars / Stripe — يُحدَّد)
- استبدال المحاكاة الداخلية بـ Business Events حقيقية
- `/upgrade` في CUPS Bot يعمل فعلاً

**قاعدة صارمة:**
```python
# ✅ صح
ctx.entitlements["atlas_access"]

# ❌ خطأ — Extension لا تقرأ Subscription أبداً
ctx.subscription.plan
```

### كيف تعرف أنها انتهت
```python
# مستخدم Starter
@bot.command("atlas")
async def use_atlas(ctx):
    if not await cups.require(ctx, entitlement="atlas_access"):
        return  # ← يصل هنا
    # ← لا يصل هنا

# مستخدم يدفع Plus عبر /upgrade → atlas_access = true → يصل للـ handler
```

---

## Phase 4 — الـ Entitlements الفعلية

**الهدف:** كل Entitlement يُفتح → شيء حقيقي يحدث.

### ما يُبنى (بالترتيب)

**tier المنفرد:**
1. `atlas_access` → `titan.atlas` يعمل للمستخدمين المؤهَّلين
2. `inspector_level` → `bot.inspect()` يعمل بمستوياته الثلاثة
3. `runtime_visibility` → `bot.health()` يعمل
4. `usage_insights` → `titan.analytics` يعمل
5. `team_access` → Team model، دعوة الأعضاء، Shared Projects

**لكل Entitlement:**
- الـ Feature موجودة في كود المنتج (Capability)
- Extension تفحص الـ Entitlement قبل السماح بالوصول
- الـ Feature تُغلَق بوضوح — لا silent failure

### ما لا يُبنى
- لا رسائل Trial أو تذكيرات (Phase 5)

### كيف تعرف أنها انتهت
```
مستخدم Plus:
  atlas_access = true → Atlas يستجيب
  usage_insights = false → titan.analytics ترفض بوضوح

مستخدم Ultra:
  جميع Entitlements = true → كل الأدوات تعمل
  Team: Core → يستطيع دعوة أعضاء
```

---

## Phase 5 — طبقة التجربة

**الهدف:** المنتج يشعر كما صمّمناه — لا فقط يعمل كما بُرمج.

### ما يُبنى

**CUPS Bot Messaging:**
- رسائل Trial End (مبنية على استخدام فعلي — Data Awareness Moments)
- رسائل الوصول للحد (نجاح، لا عقوبة)
- رسائل Trial Extension إن مُنحت
- رسائل Downgrade (احترام، لا إقناع بالرجوع)

**Relationship-aware messaging:**
- نبرة الرسائل تتغيّر بحسب المرحلة (Starter/Plus/Core/Ultra)
- لحظة Welcome after Upgrade — Ownership Moment
- رسالة عضو الفريق الجديد — Relationship Context Inheritance

**Continuous Value:**
- Atlas يستأنف السياق بصمت
- bot.health() يعمل في الخلفية
- Delight لحظة الذكرى — "هذا المشروع عمره سنة 🎉"

**CUPS-REVIEW-CHECKLIST integration:**
- في هذه المرحلة يُستخدَم الـ Checklist على كل شيء بُني في Phases 1-4
- أي انحراف يُكتشَف هنا — يُصحَّح الآن

### كيف تعرف أنها انتهت
```
مطور يصل لحد مشاريعه Starter:
  يرى: "يبدو أنك بدأت تبني بجد..." ← لا "انتهى الحد"

مطور Ultra يخفّض لـ Core:
  يرى: "كل شيء محفوظ. الطريق مفتوح." ← لا قائمة بما فقد

مطور تنتهي تجربته:
  يرى: "فتحت Atlas 17 مرة..." ← لا "تنتهي تجربتك"
```

---

## ملخص الـ Phases

| Phase | ما يُبنى | المخرج |
|---|---|---|
| 0 | فصل المستودع | CUPS له تاريخ مستقل من أول commit |
| 1 | Account + Project + Starter + Entitlement Resolution + API | النظام يعرف من أنت |
| 2 | Subscription Engine كامل (محاكاة) | Runtime نهائي قبل أن يُبنى SDK |
| 3 | titan-extension-cups + Billing حقيقي | أي Titan bot يتكامل، المستخدم يدفع |
| 4 | الـ Features الفعلية لكل Entitlement | كل حق مفتوح يُنتج قيمة حقيقية |
| 5 | الرسائل + نبرة التجربة | المنتج يشعر كما صُمِّم |

---

## ما هو خارج النطاق الآن

هذه تُبنى بعد استقرار الـ 5 Phases:

- Dashboard ويب
- SDK متعدد اللغات
- Organization model
- Enterprise Custom Plans
- Lifetime subscriptions
- Webhook بين CUPS وExtension

انظر: `ROADMAP.md` عند إنشائه.

---

> الكود الأول يُكتب في Phase 1.
> كل شيء قبل ذلك — وثائق، قرارات، فلسفة — كان خدمةً للسطر الأول.
