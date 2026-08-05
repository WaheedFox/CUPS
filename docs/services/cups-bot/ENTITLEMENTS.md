# cups-bot — Entitlements

CUPS Bot هو الباب الأمامي للمنظومة كلها — مبني فوق Titan، dogfooding حقيقي.
لكنه **ليس بلا حدود**.

---

## المبدأ

CUPS نفسه هو منتج يستهلك موارد: support، infrastructure، reporting.
ترك CUPS Bot بلا Entitlements يعني أن من يدفع أكثر لا يحصل على تجربة إدارة أفضل.

---

## قائمة Entitlements

### الوصول الأساسي

| Entitlement | النوع | الوصف |
|---|---|---|
| `cups_account_view` | Boolean | عرض حالة الاشتراك والخطة الحالية |
| `cups_projects_view` | Boolean | عرض قائمة المشاريع المسجَّلة |

> هذان متاحان للجميع — Starter وما فوق.
> لا يُعقَل أن يدفع المستخدم ولا يستطيع رؤية ما دفع مقابله.

### الإدارة المتقدمة

| Entitlement | النوع | الوصف |
|---|---|---|
| `cups_team_management` | Boolean | إضافة/إزالة أعضاء الفريق عبر CUPS Bot |
| `cups_billing_history` | Boolean | عرض سجل الفواتير والمدفوعات |
| `cups_usage_reports` | Boolean | تقارير الاستخدام التفصيلية |
| `cups_project_transfer` | Boolean | نقل مشروع لعضو آخر في الفريق |

---

## ترجمة الخطط إلى Entitlements

### Starter

```json
{
  "cups_account_view": true,
  "cups_projects_view": true,
  "cups_team_management": false,
  "cups_billing_history": false,
  "cups_usage_reports": false,
  "cups_project_transfer": false
}
```

### Plus

```json
{
  "cups_account_view": true,
  "cups_projects_view": true,
  "cups_team_management": false,
  "cups_billing_history": true,
  "cups_usage_reports": false,
  "cups_project_transfer": false
}
```

### Core

```json
{
  "cups_account_view": true,
  "cups_projects_view": true,
  "cups_team_management": true,
  "cups_billing_history": true,
  "cups_usage_reports": false,
  "cups_project_transfer": true
}
```

### Ultra

```json
{
  "cups_account_view": true,
  "cups_projects_view": true,
  "cups_team_management": true,
  "cups_billing_history": true,
  "cups_usage_reports": true,
  "cups_project_transfer": true
}
```

---

## ملاحظة معمارية

CUPS Bot يتحقق من Entitlements بنفس الآلية التي يتحقق بها أي بوت آخر مبني فوق Titan.
لا استثناء للـ Bot الداخلي — هذا جزء من اختبار CUPS لنفسه (dogfooding).
