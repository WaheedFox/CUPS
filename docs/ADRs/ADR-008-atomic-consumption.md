# ADR-008 — ذرّية Consumption وIdempotency

## الحالة

مقبول للـVertical Slice الأول

## القرار

تسجيل Consumption عملية ذرّية واحدة تشمل:

```text
idempotency lookup
    ↓
Reservation / Quota validation
    ↓
Consumption commit
    ↓
updated quota result
```

لا يجوز فصل الخصم عن تسجيل السجل. إعادة الطلب بنفس
`account_id + project_id + resource_key + idempotency_key` ونفس payload تعيد
النتيجة الملتزم بها سابقًا، ولا تنشئ Consumption ثانيًا. نفس المفتاح مع payload
مختلف يرفض بـ`IDEMPOTENCY_CONFLICT`.

`request_id` للتتبع، و`idempotency_key` لهوية العملية المنطقية. يجب أن يحمي
التخزين هذا invariants عبر transaction وقيد uniqueness؛ قفل العملية داخل
Service ليس مصدر الضمان الوحيد.

## السبب

الـRuntime سيعيد المحاولة عند timeout، وقد تصل الرسالة نفسها أكثر من مرة. لا
يكفي أن يكون المسار "غالبًا" صحيحًا؛ يجب ألا يتضاعف الاستهلاك عند retry أو
الطلبات المتزامنة.

## النطاق

هذا القرار يخص Quota وReservation وConsumption فقط. لا يضيف Billing أو Teams
أو Marketplace، ولا يجعل CUPS يعرف تفاصيل المنتج المنفّذ للعملية.