# CUPS — Documentation Map

> ليست هذه وثيقة محتوى.
> هي خريطة قرارات — تُجيب على: "ما الذي أقرأه قبل أن أفعل X؟"

---

## أريد فهم فلسفة المنتج

```
PRODUCT_PHILOSOPHY.md
```

ابدأ هنا دائماً. إذا أي قرار يتعارض مع ما فيه — توقف وناقش.

---

## أريد فهم مصطلح أو كيان

```
DOMAIN.md
```

كل مصطلح رسمي في CUPS له تعريف هنا: Account، Project، Plan، Entitlement،
Entitlement Resolution، Capability، Subscription، Team.

---

## أريد إضافة مفهوم جديد

اقرأ بالترتيب:

```
DOMAIN.md                          ← هل المفهوم موجود بشكل مختلف؟
ARCHITECTURE.md                    ← هل يؤثر على Decision Flow؟
docs/services/<product>/ENTITLEMENTS.md  ← هل يحتاج Entitlement جديداً؟
PLANS.md                           ← هل يغيّر حدود أي خطة؟
```

اسأل قبل الإضافة: هل هذا Capability أم Entitlement أم Service Commitment؟

---

## أريد إضافة Feature

اسأل ثلاثة أسئلة بالترتيب:

```
١. هل هي Capability؟
   ← تعيش في كود المنتج، ليس في CUPS

٢. هل تحتاج Entitlement؟
   ← يعني: هل سيُحدِّد CUPS من يصل إليها؟
   ← اقرأ: ENTITLEMENTS.md + DOMAIN.md (Entitlement)

٣. هل هي Service Commitment؟
   ← (مثل priority_support) لا تُفحص في runtime
   ← اقرأ: ENTITLEMENTS.md (Service Commitments section)
```

---

## أريد تغيير تجربة المستخدم أو نبرة رسالة

```
UX-PSYCHOLOGY.md       ← المبادئ النفسية والعلائقية
EXPERIENCE-JOURNEY.md  ← اللحظات المحددة في الرحلة
DATA-PRINCIPLES.md     ← إذا الرسالة تستخدم بيانات استخدام (Data Awareness)
```

---

## أريد فهم كيف تعمل البنية التقنية

```
ARCHITECTURE.md
```

يشمل: Decision Flow، Source of Truth، Authority Rule،
Consistency Model، Entitlement Resolution.

---

## أريد فهم الخطط والأسعار

```
PLANS.md
```

---

## أريد معرفة ما يُجمع من بيانات وكيف يُستخدم

```
DATA-PRINCIPLES.md
```

---

## Documentation Authority — من يفوز عند التعارض

إذا تعارضت وثيقتان، هذا هو ترتيب السلطة:

```
١. PRODUCT_PHILOSOPHY.md   ← لماذا — لا يُكسر
٢. DOMAIN.md               ← ما هي الكيانات وتعريفاتها الرسمية
٣. ARCHITECTURE.md         ← كيف تعمل المنظومة وحدودها
٤. بقية الوثائق           ← تطبيقات وتفاصيل — تخضع للثلاثة أعلاه
```

**أمثلة:**
- EXPERIENCE-JOURNEY يقترح رسالة تتعارض مع DATA-PRINCIPLES → DATA-PRINCIPLES يفوز، لأنه أقرب إلى ARCHITECTURE.
- PLANS يضيف Entitlement غير موجود في DOMAIN → DOMAIN يفوز، الإضافة تمر به أولاً.
- ENTITLEMENTS يصف سلوكاً يتعارض مع PRODUCT_PHILOSOPHY → PHILOSOPHY يفوز دائماً.

**القاعدة العملية:**
أي تعارض يحتاج قراراً معمارياً — لا يُحسَم بالكتابة فوق الوثيقة الأضعف.

**إذا تعارضت وثيقتان من نفس المستوى:**
يُرفَع القرار إلى **Maintainer Decision** ويُوثَّق في ملف ADR منفصل.
لا يُحسَم بالأغلبية، ولا يُترَك بلا توثيق.
شكل الملف: `decisions/ADR-NNN-<عنوان>.md` — يُنشأ عند الحاجة.

---

## ترتيب القراءة الموصى به لشخص جديد

```
١. PRODUCT_PHILOSOPHY.md               ← لماذا يوجد CUPS
٢. DOMAIN.md                           ← ما هي الكيانات
٣. ARCHITECTURE.md                     ← كيف تعمل المنظومة
٤. PLANS.md                            ← ما الخطط
٥. docs/services/<product>/ENTITLEMENTS.md  ← ما الحقوق لكل منتج
٦. UX-PSYCHOLOGY.md                    ← كيف نُخاطب المستخدم
٧. EXPERIENCE-JOURNEY.md               ← كيف تبدو الرحلة
٨. DATA-PRINCIPLES.md                  ← كيف نتعامل مع البيانات
```

---

## خريطة الوثائق الكاملة

```
docs/
│
├── DOCUMENTATION-MAP.md     ← أنت هنا
├── PRODUCT_PHILOSOPHY.md    ← لماذا
├── DOMAIN.md                ← ماذا (الكيانات)
├── ARCHITECTURE.md          ← كيف (المعمار)
├── PLANS.md                 ← كم (الخطط والأسعار)
├── REFERRAL-PROGRAM.md      ← عقد Referral / Commission المحاكى
├── IMPLEMENTATION-PLAN.md   ← خطة التنفيذ
├── UX-PSYCHOLOGY.md         ← كيف نُخاطب
├── EXPERIENCE-JOURNEY.md    ← ماذا يشعر المستخدم
├── DATA-PRINCIPLES.md       ← ماذا نعرف وكيف نستخدمه
├── ACCEPTANCE-SCENARIOS.md  ← سيناريوهات القبول
├── CUPS-REVIEW-CHECKLIST.md ← قائمة المراجعة
│
└── services/
    ├── titan-framework/
    │   └── ENTITLEMENTS.md  ← Entitlements خاصة بـ Titan
    └── cups-bot/
        └── ENTITLEMENTS.md  ← Entitlements خاصة بـ CUPS Bot
```

---

> إذا لم تجد إجابة في هذه الخريطة — ربما السؤال نفسه يحتاج نقاشاً.
> المعمار الجيد يُجيب على معظم الأسئلة قبل أن تُطرح.
