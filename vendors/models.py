from django.db import models

from audit.models import AuditedModel
from rfq.models import RequestForQuotation


class TaskMain(AuditedModel):
    code = models.CharField(max_length=10, unique=True)
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} · {self.name_ar}"


class TaskSub(AuditedModel):
    code = models.CharField(max_length=10, unique=True)
    main = models.ForeignKey(TaskMain, on_delete=models.PROTECT, related_name='subs')
    name_ar = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} · {self.name_ar}"


class Supplier(AuditedModel):
    REG_LOCAL = 'local'
    REG_FOREIGN = 'foreign'
    REG_STATUS_CHOICES = [
        (REG_LOCAL, 'Registered - Local'), (REG_FOREIGN, 'Registered - Foreign'),
        ('unregistered', 'Unregistered'), ('excluded', 'Excluded'),
        ('suspended', 'Suspended'), ('struck_off', 'Struck Off'),
    ]

    supplier_no = models.CharField(max_length=20, unique=True)
    legacy_id = models.CharField(max_length=20, blank=True)

    name_ar = models.CharField(max_length=255, blank=True)
    name_en = models.CharField(max_length=255, blank=True)

    registration_status = models.CharField(max_length=15, choices=REG_STATUS_CHOICES, blank=True)
    registered_local = models.BooleanField(default=False)
    registered_foreign = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    struck_off = models.BooleanField(default=False)

    dossier_no = models.CharField(max_length=50, blank=True)
    dossier_type = models.CharField(max_length=30, blank=True)
    committee_no = models.CharField(max_length=50, blank=True)
    committee_date = models.DateField(null=True, blank=True)

    commercial_registry_no = models.CharField(max_length=60, blank=True)
    commercial_registry_expiry = models.DateField(null=True, blank=True)
    tax_card_no = models.CharField(max_length=60, blank=True)
    tax_card_expiry = models.DateField(null=True, blank=True)
    vat_no = models.CharField(max_length=60, blank=True)
    vat_expiry = models.DateField(null=True, blank=True)

    capital_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    capital_currency = models.CharField(max_length=40, blank=True)

    country = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    phone1 = models.CharField(max_length=40, blank=True)
    phone2 = models.CharField(max_length=40, blank=True)
    mobile1 = models.CharField(max_length=40, blank=True)
    mobile2 = models.CharField(max_length=40, blank=True)
    fax = models.CharField(max_length=40, blank=True)
    email1 = models.CharField(max_length=120, blank=True)
    email2 = models.CharField(max_length=120, blank=True)
    website = models.CharField(max_length=150, blank=True)

    contact_person = models.CharField(max_length=150, blank=True)
    owner_name = models.CharField(max_length=150, blank=True)

    agent_name = models.CharField(max_length=200, blank=True)
    agent_phone = models.CharField(max_length=80, blank=True)
    agent_mobile = models.CharField(max_length=80, blank=True)
    agent_fax = models.CharField(max_length=80, blank=True)
    agent_email = models.CharField(max_length=120, blank=True)
    agent_address = models.TextField(blank=True)
    agency_documents = models.CharField(max_length=200, blank=True)

    category = models.CharField(max_length=100, blank=True)
    free_zone = models.BooleanField(default=False)
    certified = models.BooleanField(default=False)
    previous_no = models.CharField(max_length=30, blank=True)

    notes = models.TextField(blank=True)
    private_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['supplier_no']

    def __str__(self):
        return f"{self.supplier_no} · {self.name_ar or self.name_en}"


class SupplierQualification(AuditedModel):
    REG_TYPE_CHOICES = [
        ('supply_only', 'Supply Only'), ('supply_install', 'Supply & Install'),
        ('service', 'Service Provider'), ('rental', 'Rental / Leasing'),
    ]
    REG_CAPACITY_CHOICES = [
        ('original_manufacturer', 'Original Manufacturer'), ('sole_agent', 'Sole Agent'),
        ('commercial_agent', 'Commercial Agent'), ('authorized_distributor', 'Authorized Distributor'),
        ('other', 'Other'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='qualifications')
    task_sub = models.ForeignKey(TaskSub, on_delete=models.PROTECT, related_name='qualified_suppliers')
    registration_type = models.CharField(max_length=25, choices=REG_TYPE_CHOICES, blank=True)
    registration_capacity = models.CharField(max_length=25, choices=REG_CAPACITY_CHOICES, blank=True)
    brand = models.CharField(max_length=120, blank=True)
    original_maker = models.CharField(max_length=120, blank=True)
    origin_country = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('supplier', 'task_sub')]

    def __str__(self):
        return f"{self.supplier.supplier_no} × {self.task_sub.code}"


class ActivityProduct(AuditedModel):
    """الأنشطة — catalogue of activities and the products/services offered under each."""
    main_code = models.CharField(max_length=10, blank=True)
    main_name = models.CharField(max_length=200, blank=True)
    activity_code = models.CharField(max_length=20, blank=True)
    activity_name = models.CharField(max_length=200, blank=True)
    product_code = models.CharField(max_length=30, blank=True)
    product_service = models.CharField(max_length=255, blank=True)
    product_status = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['activity_code', 'product_code']

    def __str__(self):
        return f"{self.activity_code} {self.activity_name} · {self.product_service or '—'}"


class VendorActivity(AuditedModel):
    """موقف الموردين من الأنشطة — vendor positions vs activities incl. offered products."""
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='activities')
    vendor_name_raw = models.CharField(max_length=255, blank=True)
    activity_name = models.CharField(max_length=200, blank=True)
    main_name = models.CharField(max_length=200, blank=True)
    registration_position = models.CharField(max_length=100, blank=True)
    product_service = models.CharField(max_length=255, blank=True)
    ptype = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['vendor_name_raw', 'activity_name']

    def __str__(self):
        return f"{self.vendor_name_raw} × {self.activity_name}"


class VendorOperation(AuditedModel):
    """Vendor Opration — archived tender participation imported from the legacy system."""
    operation_no = models.PositiveIntegerField()
    year = models.CharField(max_length=10, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='operations')
    seq = models.PositiveIntegerField(null=True, blank=True)

    offer_status = models.CharField(max_length=60, blank=True)
    progress_status = models.CharField(max_length=60, blank=True)
    technical_result = models.CharField(max_length=60, blank=True)
    technical_rejection_reason = models.CharField(max_length=255, blank=True)
    certificates_status = models.CharField(max_length=60, blank=True)
    compliance = models.CharField(max_length=60, blank=True)

    initial_bond_type = models.CharField(max_length=60, blank=True)
    initial_bond_status = models.CharField(max_length=60, blank=True)
    final_bond_status = models.CharField(max_length=60, blank=True)
    supply_status = models.CharField(max_length=60, blank=True)
    late_penalty = models.CharField(max_length=60, blank=True)
    po_status = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['operation_no', 'supplier_id']

    def __str__(self):
        return f"Op {self.operation_no} ← {self.supplier.supplier_no}"


class TenderInvitation(AuditedModel):
    RESULT_PENDING = 'pending'
    RESULT_PASSED = 'passed'
    RESULT_PARTIAL = 'partial'
    RESULT_FAILED = 'failed'
    TECH_RESULT_CHOICES = [
        (RESULT_PENDING, 'Pending'), (RESULT_PASSED, 'Compliant'),
        (RESULT_PARTIAL, 'Partially Compliant'), (RESULT_FAILED, 'Non-Compliant'),
    ]
    BOND_CHOICES = [
        ('none', 'None'), ('cash', 'Cash'), ('bank_guarantee', 'Bank Guarantee'),
        ('certified_cheque', 'Certified Cheque'),
    ]
    GEN_STATUS_CHOICES = [
        ('not_yet', 'Not Yet'), ('submitted', 'Submitted'), ('accepted', 'Accepted'),
        ('refused', 'Refused'), ('exempt', 'Exempt'), ('issued', 'Issued'), ('na', 'N/A'),
    ]
    OFFER_STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'), ('submitted', 'Offer Submitted'),
        ('withdrew', 'Withdrew / Apologized'),
    ]
    SUPPLY_STATUS_CHOICES = [
        ('not_yet', 'Not Yet'), ('early', 'Delivered Early'), ('on_time', 'On Time'),
        ('late', 'Late'), ('na', 'N/A'),
    ]
    PENALTY_CHOICES = [('none', 'No Penalty Due'), ('due', 'Penalty Due'), ('applied', 'Penalty Applied')]

    rfq = models.ForeignKey(RequestForQuotation, on_delete=models.CASCADE, related_name='invitations')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='invitations')
    seq = models.PositiveIntegerField(default=0)

    offer_status = models.CharField(max_length=15, choices=OFFER_STATUS_CHOICES, default='not_submitted')
    progress_status = models.CharField(max_length=15, choices=GEN_STATUS_CHOICES, default='not_yet')
    technical_result = models.CharField(max_length=10, choices=TECH_RESULT_CHOICES, default=RESULT_PENDING)
    technical_rejection_reason = models.TextField(blank=True)
    technical_compliance = models.BooleanField(default=False)
    certificates_status = models.CharField(max_length=15, choices=GEN_STATUS_CHOICES, default='not_yet')

    initial_bond_type = models.CharField(max_length=20, choices=BOND_CHOICES, default='none')
    initial_bond_status = models.CharField(max_length=15, choices=GEN_STATUS_CHOICES, default='not_yet')
    final_bond_status = models.CharField(max_length=15, choices=GEN_STATUS_CHOICES, default='not_yet')

    financial_offer = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    financial_currency = models.CharField(max_length=10, blank=True)
    rank = models.PositiveSmallIntegerField(null=True, blank=True)

    supply_status = models.CharField(max_length=10, choices=SUPPLY_STATUS_CHOICES, default='not_yet')
    late_penalty = models.CharField(max_length=10, choices=PENALTY_CHOICES, default='none')
    po_status = models.CharField(max_length=15, choices=GEN_STATUS_CHOICES, default='not_yet')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('rfq', 'supplier')]
        ordering = ['rfq_id', 'seq']

    def __str__(self):
        return f"RFQ {self.rfq.rfq_no} ← {self.supplier}"
