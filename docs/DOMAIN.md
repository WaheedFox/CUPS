# CUPS — تعريفات المجال

هذا الملف يُعرِّف الكيانات الأساسية في CUPS بدقة.
كل تعريف هنا هو مرجع رسمي — لا يتغير إلا بقرار معماري صريح.

---

## Account

**التعريف:**
الحساب هو الكيان الأساسي في CUPS. يمثّل شخصاً حقيقياً داخل Telegram.

**الهوية:**
```
account_id = Telegram user_id
```

لا هوية بديلة في هذه المرحلة. CUPS يعمل داخل Telegram فقط.

**القواعد:**
- الحساب يُنشأ تلقائياً عند أول تفاعل مع CUPS Bot.
- لا يُحذف الحساب — يُغلق أو يُجمَّد.
- الحساب يملك Subscriptions وProjects وTeams.

---

## Project

**التعريف:**
المشروع هو وحدة الاستهلاك المسجَّلة في CUPS. يمثّل منتجاً واحداً يشغِّله المطور.

**الهوية:**
```
project_id = معرف فريد يولّده CUPS عند التسجيل
```

**CUPS لا يعلم بـ Bot Token.** Bot Token سر تشغيلي — ليس هوية مشروع.

**الهيكل:**
```
Project
├── project_id        ← معرف فريد من CUPS
├── owner_id          ← Telegram user_id صاحب المشروع
├── product           ← نوع المنتج (titan-framework, bot, mini-app, game)
├── name              ← اسم يختاره المالك
├── registered_at
└── status            ← active | suspended
```

**التسجيل:**
لا تسجيل تلقائي. المطور يُسجِّل مشروعه صراحةً عبر CUPS Bot (`/addbot`).
CUPS يُعطيه `project_id` يضعه في Extension.

```python
# في الكود
cups = CUPSGuard(api_key="...", project_id="abc123")
```

**القواعد:**
- كل مشروع مرتبط بمنتج واحد.
- الـ `project_id` هو ما يُعرِّف المشروع لـ CUPS — لا شيء آخر.
- حذف المشروع من CUPS لا يوقف البوت — الـ Extension يتعامل مع غياب التسجيل.

---

## Product

**التعريف:**
المنتج هو نوع الخدمة التي يُقدِّمها صاحب المنظومة.
كل منتج له Entitlements خاصة به — نفس الخطة تُنتج Entitlements مختلفة بحسب المنتج.

**الأنواع الحالية:**
```
titan-framework   ← مكتبة Titan + الأدوات المحيطة
bot               ← بوت Telegram مستقل
mini-app          ← Telegram Mini App
game              ← لعبة
```

**القواعد:**
- كل منتج يُعرِّف Entitlements الخاصة به بشكل مستقل.
- إضافة منتج جديد لا يغيّر الخطط أو البنية الأساسية لـ CUPS.
- كل منتج له ملف `ENTITLEMENTS.md` خاص به في `docs/services/<product>/`.
- المنتجات تُعرَّف يدوياً في **Product Catalog** — لا auto-discovery، لا registry سحري.
  (التسمية "Catalog" مقصودة: فرق بين "قائمة تعريفية" و"نظام اكتشاف تلقائي".)

---

## Plan

**التعريف:**
الخطة هي bundle تجاري — اسم تسويقي لمجموعة Entitlements بسعر محدد.

**الخطط الحالية:**
```
Starter  →  مجاني       ← الركيزة الأساسية، دائماً مجانية
Plus     →  4.99/شهر   ← رفع حدود + أدوات أساسية
Core     →  7.99/شهر   ← team_access + أدوات إنتاجية
Ultra    →  14.99/شهر  ← رفع كل القيود + أولوية الدعم
```

**الاشتراك السنوي:**
خصم سخي ومدروس — يستهدف الأفراد الراغبين في التوفير والشركات التي تريد التزاماً أطول.
القيمة الدقيقة تُحدَّد تجارياً، لكن المبدأ: السنوي يُشعر بالقيمة.

**قاعدة أساسية:**
```
الخطة = واجهة المستخدم
Entitlement = الوحدة التقنية

الكود لا يفحص Plan — يفحص Entitlement دائماً.
```

**الهيكل الهرمي:**
كل خطة تشمل كل Entitlements الخطة التي تحتها:
```
Starter ⊂ Plus ⊂ Core ⊂ Ultra
```

---

## Entitlement

**التعريف:**
Entitlement هو منح قدرة أو رفع قيد بشكل صريح ومُسمَّى.
مرتبط بمنتج محدد — ليس بخطة.

**النوعان:**
```
Boolean Entitlement   ← تفعيل/إلغاء ميزة
                         team_access: true/false

Numeric Entitlement   ← حد كمي
                         max_bots: 3
```

**مثال (titan-framework):**
```json
{
  "max_bots": 3,
  "team_access": false,
  "advanced_lint": false,
  "analytics": false,
  "priority_support": false
}
```

**القواعد:**
- Entitlement له اسم ثابت لا يتغير — حتى لو تغيّر اسم الخطة أو سعرها.
- إضافة Entitlement جديد لا تكسر Entitlements الموجودة.
- لا Entitlement "مخفي" — كل قدرة تُفتح لها اسم صريح.

---

## Capability

**التعريف:**
Capability هو قدرة تقنية موجودة داخل المنتج — يمكن التحكم في وصول المستخدم إليها عبر Entitlements.

**الفرق الجوهري:**
```
Capability  = ما يستطيع المنتج فعله
Entitlement = ما يُسمح للمستخدم بفعله
```

**مثال:**
```
Capability:   titan.atlas.memory
Entitlement:  atlas_access = true
```

**لماذا هذا التمييز مهم:**
اليوم `atlas_access: Boolean` يكفي.
لكن عندما ينمو Atlas:
```
atlas.memory
atlas.context_window
atlas.history_depth
atlas.team_memory
```
كل منها Capability مستقلة — وبدون هذا الفصل ستتضخم Entitlements وتفقد وضوحها.

**القاعدة:**
- Capability تعيش داخل المنتج — تُعرَّف في كود المنتج.
- Entitlement تعيش في CUPS — تتحكم في الوصول إلى Capability.
- لا يُغلق أي شيء خلف Entitlement إلا إذا كانت هناك Capability حقيقية قائمة بذاتها.

---

## Entitlement Resolution

**التعريف:**
Entitlement Resolution هو **عملية Domain** — ليس كياناً ثابتاً.
يحوّل Subscription إلى مجموعة Resolved Entitlements قابلة للاستهلاك مباشرة في runtime.

**الفرق الجوهري:**
```
Entitlement         = "ما الحق؟"       ← تعريف ثابت في CUPS Catalog
Entitlement Resolution = "ما الحالة الفعلية لهذا الحق الآن؟"  ← تقييم لحظي
```

**مثال:**
```
Subscription: Core
       ↓
Entitlement Resolution
       ↓
Resolved Entitlements:
  atlas_access        = true
  runtime_visibility  = true
  usage_insights      = false
  team_access         = true
  max_bots            = 20
       ↓
Runtime Checks
```

**القواعد:**
- Resolution تحدث بعد كل تغيير في Subscription (ترقية / تخفيض / انتهاء / تجديد).
- Resolved Entitlements هي ما يراه Runtime — لا شيء آخر.
- Runtime لا يُقيِّم Subscription مباشرة. يستهلك Resolved Entitlements فقط.
- في حالة التعارض أو الشك: CUPS Engine يُعيد Resolution من الصفر.

**لماذا هو كيان Domain وليس تفصيل تقني:**
بدونه، كل Extension تبدأ بالاستنتاج من بيانات Subscription — وهذا هو بالضبط الخلط الذي تمنعه قاعدة
"Runtime never evaluates subscriptions directly."

---

## Subscription

**التعريف:**
الاشتراك هو العلاقة الفعلية بين Account وخطة لمنتج معين، في فترة زمنية محددة.

**الهيكل:**
```
Subscription
├── subscription_id
├── account_id         ← صاحب الاشتراك
├── product            ← المنتج المفعَّل
├── plan               ← الخطة التجارية
├── entitlements       ← القيم الفعلية لهذا الاشتراك
├── period             ← monthly | annual
├── status             ← trial | active | grace | frozen | expired
├── started_at
├── expires_at
└── trial_ends_at      ← إن كان في فترة تجريبية
```

**دورة حياة الاشتراك:**
```
[تسجيل جديد]
      ↓
   trial          ← 3 أيام إلزامية + 4 اختيارية
      ↓
   active         ← عند الدفع
      ↓
   grace          ← عند انتهاء الدفع (فترة سماح)
      ↓
   frozen         ← تجميد الـ Entitlements المدفوعة، البيانات محفوظة
      ↓
   expired        ← بعد فترة مدروسة من التجميد
      ↓
[Starter تلقائياً]
```

**قاعدة التجربة المجانية:**
- 3 أيام إلزامية تُفتح تلقائياً عند أول اشتراك مدفوع.
- 4 أيام إضافية اختيارية (قرار تجاري متى تُعرض).
- عند انتهاء التجربة بدون دفع: العودة التلقائية لـ Starter.

**قاعدة الانتهاء:**
لا حذف فوري. التسلسل: active → grace → frozen → expired.
الفترات الزمنية لكل مرحلة تُحدَّد تشغيلياً — المبدأ ثابت.

---

## Team

**التعريف:**
الفريق طبقة collaboration فوق Account — ليس نموذج Seats.

**الفلسفة:**
Team في CUPS يعني: مطوّر واحد يدعو آخرين للعمل معه.
ليس: شركة تشتري مقاعد لموظفين.

**الهيكل:**
```
Team
├── team_id
├── owner_id       ← Account صاحب الاشتراك الذي يُغطي الفريق
├── members[]      ← [Telegram user_ids]
└── shared_resources[]  ← Projects التي يصل إليها أعضاء الفريق
```

**القواعد:**
- Team متاح فقط في خطة Core وما فوقها (`team_access: true`).
- الـ owner هو من يدفع — الأعضاء يستهلكون Entitlements من اشتراكه.
- حد عدد الأعضاء يُعرَّف كـ Entitlement: `team_members_limit`.
- **الإصدار الأول: Collaboration Model** — الفريق شراكة، ليس مقاعد موظفين.
- **Seat Model ليس مرفوضاً فلسفياً** — مؤجَّل للمرحلة التي تظهر فيها حاجة
  مؤسسية حقيقية (شركة + موظفون + أدوار منفصلة). يُضاف حينها كـ Entitlement
  مستقل دون تغيير البنية الأساسية.

**حدود Team — خط لا يُتجاوز:**
```
Team         ← مطوّر يدعو مطورين للتعاون داخل اشتراكه         ← مدعوم الآن
Organization ← كيان تجاري/قانوني بفواتير وأدوار وأذونات منفصلة ← مؤجَّل
```
أكبر فخ في أنظمة الاشتراك: الفريق الصغير يتحول تدريجياً إلى شركة،
فتبدأ الضغوط على إضافة أدوار وصلاحيات وفواتير منفصلة.
**Team ليس Organization — هذا الخط لا يُتجاوز بدون قرار معماري صريح ومدروس.**

---

## الحالة الموضَّحة

```
Account (Telegram user_id: 123456)
│
├── Subscription
│   ├── product: titan-framework
│   ├── plan: Core
│   ├── status: active
│   └── entitlements:
│       ├── max_bots: 20
│       ├── team_access: true
│       ├── team_members_limit: 5
│       ├── advanced_lint: true
│       ├── runtime_visibility: true
│       └── usage_insights: false
│
├── Projects
│   ├── { project_id: "abc", product: "titan-framework", name: "MyBot" }
│   └── { project_id: "xyz", product: "titan-framework", name: "WorkBot" }
│
└── Team
    ├── owner_id: 123456
    ├── members: [789, 1011]
    └── shared_resources: ["abc", "xyz"]
```
