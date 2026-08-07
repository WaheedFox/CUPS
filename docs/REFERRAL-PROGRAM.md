# CUPS — Referral / Commission Vertical Slice

هذه الوثيقة تصف أول إثبات داخلي لبرنامج إحالة مباشر في CUPS.
ليست Billing API، ولا تحدد النسبة أو المدة التجارية النهائية.

---

## الهدف

إثبات الرحلة التالية دون مزود دفع خارجي:

```text
Referral Code
      ↓
Account Attribution
      ↓
Successful Simulated Payment
      ↓
Eligible Commission
      ↓
Recurring Commission داخل النافذة
      ↓
Commission تتوقف عند انتهاء الأهلية
```

الإحالة مباشرة وعلى مستوى الحساب:

```text
A يحيل B → A يحصل على عمولة من دفعات B المؤهلة
B يحيل C → B يحصل على عمولة من دفعات C
A لا يحصل على عمولة من C
```

لا توجد مستويات متعددة، ولا رسوم انضمام، ولا مكافأة لمجرد التجنيد.

## حدود المرحلة الحالية

هذه العمليات داخلية ومحاكية فقط:

- إنشاء Referral Code
- تثبيت Attribution
- تسجيل دفعة محاكية ناجحة
- محاكاة Refund
- قراءة العمولات المحاكية

لا توجد في هذه المرحلة:

- Payment provider
- Webhooks
- Payouts أو دفع فعلي للمُحيل
- Public Billing API
- Dashboard
- Multi-level affiliate system

`approved` تعني أن العمولة أصبحت مؤهلة ومسجلة، ولا تعني أنها دُفعت فعلياً.
`reversed` تحفظ أثر العكس بعد Refund ولا تحذف السجل.

## القواعد

### Attribution

- Referral Code مملوك لحساب واحد.
- الحساب المُحال يرتبط بمُحيل واحد فقط.
- لا يمكن للحساب إحالة نفسه.
- لا يمكن تغيير attribution بعد تثبيته.
- وجود الحساب أو التسجيل المجاني أو Trial لا ينتج Commission.

### Eligibility

العمولة تعتمد على دفعة محاكية ناجحة مرتبطة بـ:

- الحساب المُحال
- المنتج
- Subscription موجودة
- مبلغ موجب
- Subscription مدفوعة وغير Starter
- Subscription في `active` أو `grace`

`trial` و`frozen` و`expired` لا تنتج عمولة.
حالة `active` وحدها لا تكفي؛ Starter المجاني لا يُعد اشتراكاً مدفوعاً.

### Recurring window

- تبدأ النافذة من أول دفعة مؤهلة.
- كل دفعة مؤهلة لاحقة داخل النافذة تنتج Commission مستقلة.
- لا يعاد تشغيل النافذة بسبب Upgrade أو Downgrade أو Reactivation.
- الدفعة السنوية تنتج عمولة على المبلغ المدفوع فعلياً، ولا تُحوّل إلى دفعات شهرية اصطناعية.
- مدة النافذة ونسبة العمولة configuration قابلة للتغيير، وليستا قراراً ثابتاً في `PLANS.md` أو Catalog.

### Idempotency and refunds

- `payment_id` فريد ويمنع احتساب الدفعة مرتين.
- Refund يغيّر حالة الدفع إلى `refunded`.
- Commission المرتبطة تتحول إلى `reversed`.
- تكرار Refund لا يكرر الأثر ولا يحذف السجلات.

## الحدود المعمارية

Referral طبقة تجارية مستقلة بجانب Subscription:

```text
CUPSService
├── Account
├── Project
├── Subscription
├── Entitlement Resolution
└── Referral / Commission
```

لا يعرف Referral شيئاً خاصاً بـ Titan، ولا يعرف Titan شيئاً عن Referral:

```text
Titan → Runtime → Resolved Entitlements
```

لا يتم تعديل:

- `Subscription` أو `SubscriptionStatus`
- `EntitlementEngine`
- Product Catalogs
- Runtime API
- Titan client
- Titan entitlement contract

بعد الدفعة المحاكية، يجب أن تبقى Resolved Entitlements كما هي؛ Referral لا يفتح ولا يغلق أي Capability.

## قرار مؤجل

النسبة التجارية النهائية، مدة العمولة النهائية، شروط الدفع الفعلي،
ومعالجة Chargeback كلها قرارات لاحقة مرتبطة بمرحلة Billing الحقيقية.