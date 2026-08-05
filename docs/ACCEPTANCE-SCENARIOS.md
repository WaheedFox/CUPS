# CUPS — Acceptance Scenarios

> هذه ليست Unit Tests.
> هي **توصيف سلوكي** — ما الذي يجب أن يكون صحيحاً حتى نقول إن النظام يعمل كما صُمِّم.
>
> كل سيناريو هنا مبني على قرار معماري موثَّق.
> إذا فشل سيناريو — النظام انحرف، لا الاختبار.

---

## كيف تقرأ هذه الوثيقة

```
[الحالة الابتدائية]
       ↓ [الحدث]
Runtime يجب أن يرى:
  ✅ ...    ← صحيح
  ❌ ...    ← خاطئ إذا ظهر
```

---

## ١. ترقية الخطة

### Starter → Plus

```
[Subscription: Starter, status: active]
       ↓ PaymentSucceeded → Plus
       ↓ Entitlement Resolution يُشغَّل

Runtime يجب أن يرى:
  ✅ atlas_access = true
  ✅ inspector_level = basic
  ✅ max_projects_total = 10
  ❌ team_access = true   (هذا Core فقط)
  ❌ Plan = "Plus"        (Runtime لا يرى Plan أبداً)
```

### Plus → Core

```
[Subscription: Plus, status: active]
       ↓ PaymentSucceeded → Core
       ↓ Entitlement Resolution يُشغَّل

Runtime يجب أن يرى:
  ✅ team_access = true
  ✅ runtime_visibility = true
  ✅ atlas_access = true           (موروث + محتفظ به)
  ❌ usage_insights = true         (هذا Ultra فقط)
```

### Core → Ultra

```
[Subscription: Core, status: active]
       ↓ PaymentSucceeded → Ultra
       ↓ Entitlement Resolution يُشغَّل

Runtime يجب أن يرى:
  ✅ atlas_access = true
  ✅ runtime_visibility = true
  ✅ usage_insights = true
  ✅ team_access = true
  ✅ max_projects_total = unlimited (أو الحد الأعلى)
  ❌ Plan = "Ultra"                 (Runtime لا يرى Plan)
```

---

## ٢. تخفيض الخطة (Downgrade)

### Ultra → Core

```
[Subscription: Ultra, status: active]
       ↓ Downgrade مؤكَّد → Core
       ↓ Entitlement Resolution يُشغَّل

Runtime يجب أن يرى:
  ✅ usage_insights = false         (Ultra فقط)
  ✅ atlas_access = true            (محتفظ به)
  ✅ team_access = true             (Core يدعمه)
  ✅ runtime_visibility = true

بيانات يجب أن تبقى:
  ✅ Atlas memory محفوظة
  ✅ Team members محفوظون
  ✅ Projects محفوظة
  ❌ لا حذف فوري لأي بيانات عند Downgrade
```

### Core → Plus

```
[Subscription: Core, status: active]
       ↓ Downgrade → Plus
       ↓ Entitlement Resolution يُشغَّل

Runtime يجب أن يرى:
  ✅ team_access = false
  ✅ atlas_access = true

Projects التي تجاوزت حد Plus:
  ✅ تدخل وضع read-only
  ❌ لا تُحذف
```

---

## ٣. التجربة المجانية (Trial)

### Trial نشطة

```
[Subscription: Plus, status: trial, trial_ends_at: المستقبل]
       ↓ Entitlement Resolution

Runtime يجب أن يرى:
  ✅ atlas_access = true            (Entitlements Plus كاملة)
  ✅ inspector_level = basic
  ❌ status = "trial"               (Runtime لا يرى status)
  ❌ trial_ends_at                  (Runtime لا يعرف المواعيد)
```

### Trial انتهت — بدون دفع

```
[Subscription: Plus, status: trial, trial_ends_at: الماضي]
       ↓ لا دفع
       ↓ Entitlement Resolution يُشغَّل → Starter

Runtime يجب أن يرى:
  ✅ atlas_access = false
  ✅ max_projects_total = 3          (حد Starter)
  ❌ atlas_access = true             (خطأ إذا ظل كما كان)
  ❌ "Subscription انتهت"           (Runtime لا يعرف السبب — يرى النتيجة فقط)
```

### Trial Extension مُمنوحة

```
[Subscription: Plus, status: trial, trial_ends_at: اليوم]
       ↓ CUPS يمنح 4 أيام إضافية
       ↓ trial_ends_at يتمدد
       ↓ Entitlement Resolution يُشغَّل من جديد

Runtime يجب أن يرى:
  ✅ atlas_access = true             (لا تغيير — الامتداد شفاف)
  ✅ Entitlements Plus كاملة
```

---

## ٤. دورة حياة الاشتراك المنتهي

### active → grace period

```
[Subscription: Core, status: active]
       ↓ فشل الدفع / انتهاء الفترة
       ↓ status → grace

Runtime يجب أن يرى:
  ✅ Entitlements Core كاملة (grace لا يغيير الـ Entitlements)
  ✅ team_access = true
```

### grace → frozen

```
[Subscription: Core, status: grace]
       ↓ انتهت فترة السماح
       ↓ status → frozen
       ↓ Entitlement Resolution يُشغَّل

Runtime يجب أن يرى:
  ✅ atlas_access = false            (Entitlements مدفوعة مُجمَّدة)
  ✅ team_access = false
  ✅ max_projects_total = 3          (حد Starter)
  ❌ Entitlements Core               (خطأ إذا ظلت فعّالة)

بيانات:
  ✅ Projects محفوظة
  ✅ Atlas memory محفوظة
```

### frozen → Starter (بعد expired)

```
[Subscription: Core, status: frozen → expired]
       ↓ Entitlement Resolution يُشغَّل → Starter

Runtime يجب أن يرى:
  ✅ Entitlements Starter فقط
  ✅ الحساب يعمل كـ Starter طبيعي
  ❌ أي أثر من Core في Resolved Entitlements
```

---

## ٥. عزل الـ Runtime — القاعدة الأساسية

هذه السيناريوهات تختبر قاعدة: `Runtime MUST NEVER evaluate subscriptions directly`

```
سيناريو: Extension تطلب Plan مباشرة
  ❌ المتوقع: Extension لا تحصل على Plan name أبداً
  ✅ Extension تحصل فقط على: { atlas_access: true/false, ... }

سيناريو: تغيّرت Subscription لكن Cache لم يُبطَل بعد
  ✅ Runtime يرى Resolved Entitlements القديمة حتى انتهاء الـ Cache
  ✅ بعد انتهاء Cache أو Invalidation: يرى الحالة الجديدة
  ❌ Runtime يقرأ Subscription مباشرة للتحقق — هذا كسر للقاعدة

سيناريو: تعارض بين Cache وCUPS Engine
  ✅ CUPS Engine هو المرجع النهائي دائماً
  ✅ Cache تُبطَل ويُعاد Resolution
```

---

## ٦. Relationship Context Inheritance — عضو فريق جديد

```
[Account: Ultra, Team: owner=A, members=[B]]
       ↓ C ينضم للفريق

Runtime يجب أن يرى لـ C:
  ✅ Entitlements Ultra (من اشتراك صاحب الحساب)
  ✅ team_access = true

تجربة C:
  ✅ يُستقبل بنبرة الحساب (شراكة — لأن الحساب Ultra)
  ✅ يُقدَّم له المنتج بنبرة البداية (سياق، لا افتراضات)
  ❌ لا يُعامَل كـ Ultra ذي خبرة لأن حسابه Ultra
  ❌ لا يُعامَل كـ Starter لأنه جديد
```

---

## ٧. كيف تُستخدم هذه السيناريوهات

هذه الوثيقة مرجع لثلاثة أنواع من القرارات:

| الموقف | الاستخدام |
|---|---|
| قبل كتابة كود جديد | تحقق: هل السيناريو المعني موثَّق هنا؟ |
| عند مراجعة Pull Request | اختبر: هل السيناريوهات المتأثرة لا تزال صحيحة؟ |
| عند ظهور Bug | اسأل: أي سيناريو انكسر؟ ولماذا؟ |

---

> النظام الذي لا يُوصَف سلوكه المتوقع
> لا يُعرَف متى ينكسر.
