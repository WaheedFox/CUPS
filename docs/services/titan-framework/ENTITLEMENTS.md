# titan-framework — Entitlements

هذا الملف يُعرِّف كل Entitlement لمنتج `titan-framework` ويُترجم كل خطة إلى قيم فعلية.

---

## المبدأ الأساسي

**المكتبة نفسها — `pip install titan-framework` — مجانية دائماً.**
ما يُفتح بالاشتراك هو **طبقة الأدوات المحيطة**: أدوات المطور، أدوات الفريق، أدوات الإنتاج.

الفرق: Titan يعمل للجميع. CUPS يُفتح مستويات عمل أعلى.

---

## ما هو مجاني دائماً (Starter Core)

هذه المكوّنات متاحة لكل مستخدم Titan — بلا اشتراك، بلا قيود:

| المكوّن | الوصف |
|---|---|
| `Titan`, `Router`, `Context` | الإطار الأساسي |
| `Middleware`, `MiddlewareChain` | سلسلة التنفيذ |
| `Adapter`, `Update` | ترجمة Telegram updates |
| `Telegram` client | الاتصال بـ Telegram API |
| `Message`, `Sender`, `Chat` | نماذج البيانات الأساسية |
| `InlineKeyboard`, `InlineButton` | لوحة المفاتيح |
| `TitanError`, `TelegramError` | هرمية الأخطاء |
| `titan.extras` (AskManager, AliasMap) | أدوات مساعدة |
| `titan.recipes.welcome` | الوصفة الأساسية |
| `titan.validation` | التحقق من صحة الـ handlers |
| `titan.lifecycle` | إدارة polling والإيقاف الآمن |
| `titan.links` | **هوية Titan نفسها** — بروتوكول ربط الرسائل، مجاني دائماً |
| `titan.privacy` | بروتوكول خصوصية البيانات — التزام قانوني |
| `titan.migration` | مساعد الترحيل — يُخفِّض حاجز الانتقال لـ Titan |

> **ملاحظة `titan.links`:** هذه ليست ميزة مُضافة — هي جزء من هوية Titan كإطار.
> إغلاقها خلف Entitlement يعني إغلاق قدرة جوهرية عن مستخدم يستحقها بالفعل.

---

## أنواع Entitlements

### Boolean
قيمة تشغيل/إيقاف.
```
atlas_access: true | false
```

### Numeric
حد كمي.
```
max_projects_total: 3
```

### Capability Tier *(نوع جديد)*
مستوى وصول متعدد الدرجات — ليس مفتاحاً ثنائياً.
```
inspector_level: none | basic | advanced
```

**لماذا هذا النوع ضروري:**
الأدوات ليست دائماً مفتاح تشغيل/إيقاف.
Inspector للمبتدئ يُعطي نظرة عامة — Inspector للمحترف يُعطي تاريخاً وتتبعاً كاملاً.
نفس الأداة، مستويات مختلفة، قيمة مختلفة.

---

## قائمة Entitlements

### الحدود الكمية

| Entitlement | النوع | الوصف |
|---|---|---|
| `max_projects_total` | Numeric | إجمالي المشاريع المسجَّلة في CUPS عبر كل المنتجات |
| `team_members_limit` | Numeric | عدد أعضاء الفريق (`0` = لا فريق) |

> **`max_projects_total` is across all products** — ليس per-product.
> 3 projects = 3 مشاريع إجمالاً، بغض النظر إن كانت Titan بوتات أو Mini Apps أو ألعاب.
> هذا يمنع الالتفاف (Titan: 3 + Games: 3 + Apps: 3 = 9 فعلياً).
> مستقبلاً: شركات تحتاج product-specific limits → تُضاف كـ Entitlements منفصلة.

### أدوات المطور (Developer Workflow)

| Entitlement | النوع | الوصف |
|---|---|---|
| `atlas_access` | Boolean | `titan.atlas` — الذاكرة المعمارية والـ AI assistant |
| `lint_advanced` | Boolean | `bot.lint()` — قواعد lint متقدمة |
| `inspector_level` | Capability Tier | `bot.inspect()` — none / basic / advanced |
| `playground_access` | Boolean | `titan.playground` — بيئة اختبار البوت |
| `profiler_access` | Boolean | `titan.profiler` — قياس الأداء |
| `timeline_access` | Boolean | `titan.timeline` — سجل التطور المعماري |

### أدوات الإنتاج (Production Workflow)

| Entitlement | النوع | الوصف |
|---|---|---|
| `runtime_visibility` | Boolean | `bot.health()` — رؤية ما يحدث في الإنتاج. القيمة: "بوتك يعمل ليلاً، وأنت تعرف كيف حاله في الصباح." |
| `usage_insights` | Boolean | `titan.analytics` — فهم سلوك مستخدمي البوت: أين يتوقفون، أي أمر يُتخلى عنه في منتصف الطريق، المسار الأكثر استخداماً. القيمة: معرفة، لا مجرد أرقام. |

### Team

| Entitlement | النوع | الوصف |
|---|---|---|
| `team_access` | Boolean | إمكانية إنشاء فريق وإضافة أعضاء |

---

## ملاحظة معمارية — هذه القيم ليست نهائية بذاتها

القيم المُعرَّفة في هذا الملف هي **input** لـ Entitlement Resolution.
Runtime لا يقرأ هذا الملف مباشرة — يقرأ **Resolved Entitlements** الصادرة عن CUPS Entitlement Engine.

```
ENTITLEMENTS.md (هذا الملف)
       ↓  تعريف القيم النظرية
Entitlement Resolution  (CUPS Engine)
       ↓  حساب الحالة الفعلية للاشتراك
Resolved Entitlements
       ↓  ما يستهلكه Runtime
Extension (titan-extension-cups)
```

انظر: `DOMAIN.md` — كيان `Entitlement Resolution` للتفاصيل.

---

## هوية كل خطة

| الخطة | الهوية |
|---|---|
| Starter | أتعلم وأبني |
| Plus | أطور باحتراف |
| Core | أشغّل وأتعاون |
| Ultra | أدير منظومة |

كل انتقال له قصة — ليس مجرد سعر أعلى.

---

## ترجمة الخطط إلى Entitlements

### Starter — مجاني | أتعلم وأبني

```json
{
  "max_projects_total": 3,
  "team_members_limit": 0,
  "atlas_access": false,
  "lint_advanced": false,
  "inspector_level": "basic",
  "playground_access": false,
  "profiler_access": false,
  "timeline_access": false,
  "runtime_visibility": false,
  "usage_insights": false,
  "team_access": false
}
```

**ما يعمل:** الإطار كاملاً + Inspector بشكل محدود (basic state فقط، لا history).
**لماذا Inspector Basic وليس none:** Starter يجب أن يكون تجربة عادلة، لا نسخة مشلولة.
**ما لا يعمل:** Atlas، Lint المتقدم، Playground، Profiler، Timeline، Health، Team.

**Inspector Basic يعني:**
- ✓ عرض حالة البوت الحالية (handlers، middleware، state)
- ✗ تاريخ التغييرات
- ✗ المقارنة بين لحظتين

---

### Plus — $4.99/شهر | $49/سنة | أطور باحتراف

```json
{
  "max_projects_total": 10,
  "team_members_limit": 0,
  "atlas_access": true,
  "lint_advanced": true,
  "inspector_level": "advanced",
  "playground_access": true,
  "profiler_access": true,
  "timeline_access": true,
  "runtime_visibility": false,
  "usage_insights": false,
  "team_access": false
}
```

**ما يفتح:** حزمة Developer Workflow كاملة.
**الجمهور:** المطور الجاد الذي يبني باحتراف ويهتم بجودة الكود.

---

### Core — $7.99/شهر | $79/سنة | أشغّل وأتعاون

```json
{
  "max_projects_total": 20,
  "team_members_limit": 5,
  "atlas_access": true,
  "lint_advanced": true,
  "inspector_level": "advanced",
  "playground_access": true,
  "profiler_access": true,
  "timeline_access": true,
  "runtime_visibility": true,
  "usage_insights": false,
  "team_access": true
}
```

**ما يفتح فوق Plus:** runtime_visibility (رؤية الإنتاج) + Team (تعاون حتى 5 أعضاء).
**الفصل الواضح:** Plus = Developer Workflow / Core = Production Workflow + Team.

---

### Ultra — $14.99/شهر | $149/سنة | أدير منظومة

```json
{
  "max_projects_total": 100,
  "team_members_limit": 20,
  "atlas_access": true,
  "lint_advanced": true,
  "inspector_level": "advanced",
  "playground_access": true,
  "profiler_access": true,
  "timeline_access": true,
  "runtime_visibility": true,
  "usage_insights": true,
  "team_access": true
}
```

**ما يفتح فوق Core:** usage_insights (فهم سلوك المستخدمين) + فريق حتى 20 عضواً.

---

## Service Commitments — خارج Entitlements

هذه ليست قدرات داخل المنتج — هي التزامات في العلاقة مع الفريق.

**الفرق الجوهري:**
```
Product Entitlement  = يغيّر ما يفعله البرنامج
Service Commitment   = يغيّر كيف يتعامل الفريق مع المستخدم
```

| Commitment | المعنى |
|---|---|
| `priority_support` | وقت استجابة أولوي من الفريق (Ultra) |
| `dedicated_contact` | نقطة تواصل مباشرة (مستقبلاً، للشركات) |

**ملاحظة:** هذه الالتزامات تُذكر في صفحة الأسعار — لكنها لا تنتمي لجدول Entitlements التقنية ولا تُفحص في runtime. الكود لا يعرف بها.

---

## كيف يستخدم الكود Entitlements

```python
# Boolean — تشغيل/إيقاف
if not await cups.require(ctx, entitlement="atlas_access"):
    return

# Numeric — حد كمي
limit = await cups.value(ctx, entitlement="max_projects_total")

# Capability Tier — مستوى وصول
level = await cups.tier(ctx, entitlement="inspector_level")
if level == "none":
    return
show_basic = level in ("basic", "advanced")
show_advanced = level == "advanced"

# ❌ خطأ — لا تفحص Plan مباشرةً
if user_plan == "plus":
    ...
```

---

## إضافة Entitlement جديد

1. حدد النوع: Boolean / Numeric / Capability Tier.
2. أضف السطر في الجدول المناسب أعلاه.
3. حدد قيمته في كل خطة من الأربع.
4. Starter يحصل على القيمة الأكثر تقييداً.
5. استخدم الاسم مباشرةً في الكود.

**لا تغيير في اسم الخطة. لا تغيير في CUPS بنية.**
