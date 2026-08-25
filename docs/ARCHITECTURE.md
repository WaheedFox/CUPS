# CUPS — المعمار

كيف تعمل المنظومة. هذا الملف يصف الهيكل، التدفق، والحدود.

---

## مكوّنات CUPS Platform

```
CUPS Platform
├── CUPS Bot           ← الباب الأمامي — كل تفاعل مستخدم يمر هنا
├── Entitlement Engine ← قلب النظام — يُقيّم ما يملكه المستخدم
├── Product Catalog    ← تعريفات المنتجات وEntitlements كل منها (لا auto-discovery)
│   └── Capabilities   ← ما يستطيع المنتج فعله (مستقل عن ما يُسمح للمستخدم)
├── Billing            ← إدارة الدفع والتجديد والتجريب
└── Extensions         ← الجسور بين CUPS والمنتجات
    └── titan-extension-cups  ← التكامل مع Titan
```

**الفصل بين Capability وEntitlement:**
```
Capability  = تعريف داخل المنتج — "ماذا يستطيع البرنامج؟"
Entitlement = تعريف داخل CUPS  — "ماذا يُسمح للمستخدم؟"
```
هذا الفصل يجعل المنتج ينمو (تُضاف Capabilities) بدون أن تتضخم Entitlements.

---

## CUPS Bot — الباب الأمامي

CUPS Bot هو بوت Telegram مبني فوق Titan.
كل تفاعل مع CUPS يمر عبره: تسجيل المشاريع، إدارة الاشتراكات، عرض الخطط.

**لماذا بوت Telegram وليس واجهة ويب؟**
لأن المنظومة كلها داخل Telegram. المستخدم لا يغادر بيئته.
وهذا يُثبّت أن CUPS يأكل طعامه — مبني فوق نفس الأدوات التي يُقدِّمها.

**أوامر أساسية:**
```
/start        ← إنشاء أو استرجاع Account
/addbot       ← تسجيل مشروع جديد → يُعطي project_id
/myprojects   ← عرض المشاريع المسجَّلة
/plan         ← عرض الخطة الحالية والـ Entitlements
/upgrade      ← الترقية لخطة أعلى
/team         ← إدارة الفريق (Core+)
```

---

## تدفق التسجيل — كيف يُسجِّل مطور مشروعه

```
المطور يفتح CUPS Bot
      ↓
/addbot
      ↓
CUPS: "ما اسم المشروع؟ ما نوعه؟"
(titan-framework / bot / mini-app / game)
      ↓
CUPS يُنشئ Project:
{ project_id: "abc123", product: "titan-framework", owner_id: user_id }
      ↓
CUPS Bot يُرسل للمطور:
"مشروعك مسجَّل. project_id: abc123"
      ↓
المطور يضع project_id في الكود:
cups = CUPSGuard(api_key="...", project_id="abc123")
```

لا Bot Token يُرسَل لـ CUPS. لا تسجيل تلقائي. لا magic.

---

## تدفق التحقق من Entitlement — runtime

عندما يطلب مستخدم ميزة مدفوعة:

```
المستخدم يرسل أمراً في البوت
      ↓
Titan يمرر ctx للـ middleware chain
      ↓
CUPSGuard.as_middleware() يُشغَّل
(يستخرج ctx.user_id)
      ↓
CUPSGuard يسأل CUPS Service:
{
  user_id: 123,
  project_id: "abc123",
  entitlement: "advanced_lint"
}
      ↓
CUPS Entitlement Engine يُقيّم:
- هل للمستخدم subscription نشطة للمنتج؟
- ما قيمة "advanced_lint" في اشتراكه؟
      ↓
CUPS يُجيب: { granted: true/false, value: ... }
      ↓
CUPSGuard يُقرر: يكمل next() أو يُوقف ويُبلِّغ المستخدم
```

---

## حدود التكامل — Titan ↔ CUPS

```
ما يحتاجه titan-extension-cups من Titan:

bot.middleware()    ← Extension Point الوحيد (CONTRACT §16)
ctx.user_id         ← لتحديد هوية المستخدم
ctx.reply()         ← للتواصل مع المستخدم عند رفض الـ Entitlement
```

هذا كل شيء. Titan Core لا يعلم بـ CUPS، ولا يحتاج أن يعلم.

**النمط:**
```python
from titan_extension_cups import CUPSGuard

cups = CUPSGuard(api_key="...", project_id="abc123")
bot.middleware(cups.as_middleware())

@bot.command("export")
async def export_data(ctx):
    if not await cups.require(ctx, entitlement="data_export"):
        return  # CUPSGuard أعلم المستخدم وأوقف التنفيذ
    # ... المنطق الفعلي
```

---

## فصل المسؤوليات

| المسؤولية | من يتولاها |
|---|---|
| تعريف Entitlements لكل منتج | CUPS Product Catalog (تعريف يدوي، لا auto-discovery) |
| تقييم ما يملكه المستخدم | CUPS Entitlement Engine |
| تسجيل المشاريع | CUPS Bot |
| إدارة الدفع | CUPS Billing |
| فحص Entitlement في runtime | titan-extension-cups |
| توجيه الـ updates | Titan Core |
| منطق البوت | المطور |

لا مسؤولية تتقاطع. كل طرف يعرف دوره.

---

## Decision Flow — اتجاه التبعية

الطبقات العليا تُعرِّف المعنى. الطبقات السفلى تُنفِّذ التجربة.

```
Philosophy      ← لماذا يوجد CUPS
     ↓
Domain          ← ما هي الكيانات وتعريفاتها
     ↓
Product Catalog ← ماذا يستطيع كل منتج أن يفعل
     ↓
Capabilities    ← القدرات التقنية الموجودة داخل المنتج
     ↓
Entitlements    ← ما يُسمح للمستخدم بالوصول إليه
     ↓
Plans           ← bundle تجاري من Entitlements بسعر محدد
     ↓
Subscriptions          ← العلاقة الفعلية بين مستخدم وخطة في وقت محدد
     ↓
Entitlement Resolution ← تحويل Subscription إلى Resolved Entitlements
     ↓
Runtime                ← يستهلك Resolved Entitlements فقط — لا يقيّم Subscription
     ↓
Experience             ← ما يشعر به المستخدم في كل لحظة
```

**القواعد الصارمة:**
- Runtime لا يعرف Plan — يعرف Entitlement فقط
- Experience لا تُعرِّف Capability — تعكسها فقط
- Plan لا يخترع Entitlement — يجمع ما هو موجود بالفعل
- أي تغيير في طبقة يُسأل: "هل يؤثر على الطبقات تحته؟"

---

## Source of Truth — من يعرف ماذا

أكبر خطر مستقبلي: كل منتج يبدأ بتفسير Entitlements بطريقته.

```
Product Catalog       ← يعرف أسماء Entitlements (لا معناها التشغيلي)
       ↓
Entitlement Engine    ← يعرف قيمة كل Entitlement لكل مستخدم
       ↓
Product Extension     ← يعرف كيف يُطبِّق الـ Entitlement داخل المنتج
```

**Authority Direction — من يحدد ومن ينفّذ:**
```
CUPS Engine          ← يُحدِّد الإذن  "هل يملك المستخدم هذه القدرة؟"
       ↓
Entitlement Engine   ← يُحلّ القيمة  "ما القيمة الفعلية لهذا الاشتراك؟"
       ↓
Extension            ← يُنفِّذ السلوك "ما الذي يحدث بناءً على هذا الإذن؟"
```

**القاعدة الجوهرية:**
> CUPS determines permission. Extensions enforce behavior.

Extension ليست أقل أهمية — هي فقط ليست مصدر الحقيقة.

مثال:
- CUPS: "`atlas_access` = false لهذا الحساب."
- Extension: "أخفي واجهة Atlas، وأمنع تنفيذ أي استدعاء لها."

الفصل يمنع أي Extension من "إعادة تفسير" ما يملكه المستخدم.

---

## Consistency Model — الحالة ليست فورية

Billing state ليست Runtime state مباشرة.

```
Billing Event (دفع / انتهاء / ترقية)
        ↓
Subscription Update في CUPS
        ↓
Entitlement Resolution   ← هنا تُحسب القيم الفعلية
        ↓
Runtime Cache            ← ما يراه Extension في كل طلب
        ↓
Expiration / Invalidation ← عند تغيير الاشتراك
```

**القاعدة الأساسية — غير قابلة للكسر:**
> Runtime MUST NEVER evaluate subscriptions directly.
> Runtime MUST consume resolved entitlements only.

`MUST NEVER` هنا تعني: لا استثناء، لا "في حالة الطوارئ"، لا "مؤقتاً".
أي Extension تقرأ Subscription مباشرة تكسر هذه القاعدة — بغض النظر عن السبب.

هذه القاعدة تمنع تكرار الخطأ القديم بطريقة جديدة:
اليوم قد يتغير Plan، يتأخر Billing، أو يكون Cache قديماً.
إذا بدأ أي Extension بتفسير Subscription مباشرة — تتباين النتائج عبر المنظومة.

**المبادئ (بدون تفاصيل تقنية الآن):**
- Runtime يعتمد على Resolved Entitlements — لا على Billing state أو Subscription مباشرة.
- Cache له expiry معقول — لا يبقى إلى ما لا نهاية.
- عند تغيير الاشتراك: Cache يُبطَل أو يُجدَّد في أقرب وقت.
- في حالة التعارض: CUPS Engine هو المرجع النهائي دائماً.

**الأرقام والتفاصيل التقنية:** تُحدَّد عند التنفيذ — المبدأ ثابت.

---

## Resource Usage — ذرّية Consumption

CUPS لا ينفذ العملية التي يستهلك المنتج من أجلها المورد. لكنه يملك قرار
الحجز وتسجيل الاستهلاك، ولذلك يجب أن يكون تسجيل Consumption ذريًا:

```text
idempotency lookup
    ↓
validate Reservation / Quota
    ↓
commit Consumption + usage state
    ↓
return the committed quota result
```

إعادة الطلب بنفس `idempotency_key` ونفس payload تعيد النتيجة الأصلية ولا تخصم
المورد مرة أخرى. اختلاف payload مع المفتاح نفسه يرفض بـ
`IDEMPOTENCY_CONFLICT`. يضمن ذلك كل من transaction وقيد uniqueness في التخزين؛
أما `request_id` فهو للتتبع فقط.

---

## هيكل المستودع

```
cups-repo/
├── README.md
├── pyproject.toml
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── DOCUMENTATION-MAP.md  ← خريطة الوثائق
│   ├── PHILOSOPHY.md         ← لماذا يوجد CUPS
│   ├── PRODUCT_PHILOSOPHY.md ← فلسفة المنتج
│   ├── DOMAIN.md             ← تعريفات الكيانات
│   ├── ARCHITECTURE.md       ← هذا الملف
│   ├── PLANS.md              ← الخطط والأسعار
│   ├── IMPLEMENTATION-PLAN.md
│   ├── UX-PSYCHOLOGY.md
│   ├── EXPERIENCE-JOURNEY.md
│   ├── DATA-PRINCIPLES.md
│   ├── ACCEPTANCE-SCENARIOS.md
│   ├── CUPS-REVIEW-CHECKLIST.md
│   │
│   └── services/
│       ├── titan-framework/
│       │   └── ENTITLEMENTS.md   ← Entitlements الخاصة بـ Titan
│       ├── cups-bot/
│       │   └── ENTITLEMENTS.md   ← Entitlements الخاصة بـ CUPS Bot
│       ├── bots/             ← مستقبلاً
│       ├── mini-apps/        ← مستقبلاً
│       └── games/            ← مستقبلاً
│
├── src/
│   └── cups/             ← CUPS Platform
│       └── core/         ← Core sub-package
│
├── apps/
│   └── cups-bot/         ← CUPS Bot Application
│
└── tests/
```

**قاعدة:**
كل خدمة جديدة تضيف مجلدها تحت `docs/services/` مع ملف `ENTITLEMENTS.md` خاص بها.
لا تغيير في PHILOSOPHY أو DOMAIN أو ARCHITECTURE — إلا إذا تغيّرت المبادئ نفسها.

---

## ما لا يُبنى الآن

هذه الأشياء خارج النطاق الحالي — تُعاد دراستها عند الحاجة الفعلية:

| الشيء | السبب |
|---|---|
| Webhook بين CUPS وExtension | Polling كافٍ في المرحلة الأولى |
| SDK متعدد اللغات | الهدف الآن Python فقط |
| Dashboard ويب | المنظومة داخل Telegram |
| Enterprise Custom Plans | تُضاف لاحقاً كـ Entitlement خاص |
| Lifetime subscriptions | يحتاج دراسة مستقلة |
| Migration CLI | لا ضغط فعلي الآن |
