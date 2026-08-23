from django.db import models

from audit.models import AuditedModel
from rfq.models import RequestForQuotation
from vendors.models import Supplier


class PurchaseOrder(AuditedModel):
    PAYMENT_CHOICES = [
        ('cheque_on_inspection', 'Cheque on Inspection & Receipt'),
        ('cheque_after_receipt', 'Cheque after Inspection & Receipt'),
        ('lc', 'Letter of Credit'),
        ('bank_transfer', 'Bank Transfer'), ('cash', 'Cash'), ('other', 'Other'),
    ]
    CURRENCY_CHOICES = [
        ('EGP', 'EGP'), ('USD', 'USD'), ('EUR', 'EUR'), ('SAR', 'SAR'), ('AED', 'AED'),
    ]

    CHECKLIST_FIELDS = [
        ('items_delivered', 'تم توريد المهمات المطلوبة / Required items delivered'),
        ('qty_delivered', 'تم توريد الكمية المطلوبة / Full quantity delivered'),
        ('on_time', 'تم التوريد فى الموعد المحدد / Delivered on time'),
        ('right_place', 'تم التوريد فى المكان المحدد / Delivered to correct place'),
        ('per_specs', 'تم التوريد مطابق للمواصفات / Matches specifications'),
        ('po_form_complete', 'تعبئة أمر التوريد سليمة / PO form completed properly'),
        ('docs_complete', 'إكتمال مستندات العملية و الفاتورة / Documents & invoice complete'),
    ]

    rfq = models.ForeignKey(RequestForQuotation, null=True, blank=True,
                            on_delete=models.SET_NULL, related_name='purchase_orders')
    legacy_op_no = models.CharField(max_length=20, blank=True)
    supplier = models.ForeignKey(Supplier, null=True, blank=True,
                                 on_delete=models.PROTECT, related_name='purchase_orders')

    po_no = models.CharField(max_length=30)
    po_date = models.DateField(null=True, blank=True)
    year = models.PositiveIntegerField(default=2026)

    items_description = models.TextField(blank=True)
    value = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='EGP')
    payment_method = models.CharField(max_length=25, choices=PAYMENT_CHOICES, blank=True)
    cheque_no = models.CharField(max_length=40, blank=True)
    cheque_date = models.DateField(null=True, blank=True)

    lc_open_date = models.DateField(null=True, blank=True)
    lc_receipt_date = models.DateField(null=True, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    amount_egp = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    amount_usd = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    delivery_days = models.PositiveIntegerField(null=True, blank=True)
    delivery_start_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    delivery_place = models.CharField(max_length=200, blank=True)
    shipping_method = models.CharField(max_length=100, blank=True)
    goods_receipt_no = models.CharField(max_length=40, blank=True)
    shipping_docs_date = models.DateField(null=True, blank=True)
    customs_clearance_date = models.DateField(null=True, blank=True)
    disbursement_request_date = models.DateField(null=True, blank=True)
    bond_refund_date = models.DateField(null=True, blank=True)

    items_delivered = models.BooleanField(default=False)
    qty_delivered = models.BooleanField(default=False)
    on_time = models.BooleanField(default=False)
    right_place = models.BooleanField(default=False)
    per_specs = models.BooleanField(default=False)
    po_form_complete = models.BooleanField(default=False)
    docs_complete = models.BooleanField(default=False)

    followup_by = models.CharField(max_length=150, blank=True)
    sap_no = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    po_image = models.FileField(upload_to='po_images/', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-po_no']

    def __str__(self):
        sup = self.supplier.name_ar if self.supplier_id else (self.supplier or '')
        return f"PO {self.po_no} · {str(sup)[:40]}"

    @property
    def checklist_done(self):
        return sum(1 for f, _ in self.CHECKLIST_FIELDS if getattr(self, f))

    @property
    def checklist_total(self):
        return len(self.CHECKLIST_FIELDS)
