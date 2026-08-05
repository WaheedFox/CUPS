# CUPS — Review Checklist

> قبل أي Pull Request يؤثر على CUPS.
> هذا ليس bureaucracy — هو الفرق بين منتج يحافظ على فلسفته وآخر ينحرف بهدوء.

---

## ١. الـ Capability

- [ ] هل أضفت قدرة تقنية جديدة للمنتج؟
  - هل هي موجودة في كود المنتج (وليس في CUPS)؟
  - هل وثّقتها ضمن Capabilities في ARCHITECTURE.md؟

---

## ٢. الـ Entitlement

- [ ] هل تحتاج Entitlement جديداً لهذه الـ Capability؟
  - هل الاسم واضح ويصف **القيمة** لا الخوف؟ (`usage_insights` لا `analytics_block`)
  - هل أضفته في `ENTITLEMENTS.md` للمنتج المعني؟
  - هل أضفته في `DOMAIN.md` إذا غيّر نموذج المجال؟
  - هل هو Boolean أم Numeric أم Capability Tier؟ (اختر الأنسب)

---

## ٣. هل هو Service Commitment لا Entitlement؟

- [ ] هل ما تُضيفه وعد تشغيلي (مثل أولوية الدعم) لا قدرة تُفحص في runtime؟
  - إذا نعم: يذهب إلى قسم **Service Commitments** في ENTITLEMENTS.md — لا يُفحص في runtime أبداً.

---

## ٤. الرسائل والتجربة

- [ ] هل الرسالة تناسب **مرحلة العلاقة** (Relationship Level) للمستخدم؟
  - Starter: دعوة بلا ضغط
  - Plus/Core: اعتراف بالنضج
  - Ultra: شراكة، لا بيع

- [ ] هل تستخدم الرسالة Experience Signal؟
  - هل تُجيب سؤالاً واحداً فقط: **"لماذا وصلتني هذه الرسالة؟"**
  - هل تمنع المستخدم من الشعور بالمراقبة؟

---

## ٥. البيانات

- [ ] هل تجمع بيانات جديدة؟
  - هل هي Operational Signal أم Experience Signal أم Business Signal؟ (راجع DATA-PRINCIPLES.md)
  - هل تخدم المستخدم نفسه أم أهدافاً داخلية؟
  - هل تجاوزت الـ CUPS Intelligence Boundary؟ (تعرف ما يكفي، وتتوقف عند الحد)

- [ ] هل Extension تطلب بيانات أكثر مما تحتاج؟
  - Extensions تحتاج: هل يملك المستخدم هذا الـ Entitlement؟ — لا أكثر.

---

## ٦. الـ Runtime

- [ ] هل أي كود يُقيّم Subscription مباشرة؟
  - **إذا نعم: STOP.** هذا يكسر القاعدة الأساسية.
  - Runtime MUST NEVER evaluate subscriptions directly.
  - Runtime MUST consume Resolved Entitlements only.

---

## ٧. الـ Flow

- [ ] هل غيّرت Decision Flow؟
  - راجع: `ARCHITECTURE.md` — Decision Flow
  - تحقق: هل التغيير يؤثر على طبقة أسفله؟

- [ ] هل أضفت كياناً جديداً في Domain؟
  - أضفه في `DOMAIN.md` — لا تتركه مُستنتَجاً من الكود.

---

## ٨. الـ Continuous Value

- [ ] هل يوجد قيمة في "الأيام التي لا يحدث فيها شيء"؟
  - الميزة الجيدة تُثبت قيمتها في اليوم العادي — لا فقط في لحظة الترقية.

---

## ٩. الفلسفة — السؤال الأخير

- [ ] هل هذا التغيير يتوافق مع PRODUCT_PHILOSOPHY.md؟
  - نبيع **قيمة**، لا نرفع قيوداً.
  - لا Artificial Scarcity.
  - لا Growth Without Migration Pain.

> إذا أجبت "لا" على أي سؤال — لا يعني ذلك رفض التغيير.
> يعني أنك تحتاج قراراً معمارياً واعياً، لا مجرد كود يُدمج.
