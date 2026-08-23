from django.conf import settings
from django.db import models
from django.utils import timezone

from audit.models import AuditedModel


class Client(AuditedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} · {self.name}"


class CostCenter(AuditedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} · {self.name}"


class Location(AuditedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} · {self.name}"


class Project(AuditedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name='projects')
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} · {self.name}"


class RequestForQuotation(AuditedModel):
    STATUS_NEW = 'new'
    STATUS_REVIEW = 'review'
    STATUS_LISTING = 'vendor_listing'
    STATUS_SUBMITTED = 'list_submitted'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_REVIEW, 'Under Review'),
        (STATUS_LISTING, 'Building Vendor List'),
        (STATUS_SUBMITTED, 'Vendor List Submitted'),
        (STATUS_APPROVED, 'Vendor List Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    EXEC_DIRECT = 'direct_order'
    EXEC_TENDER = 'public_tender'
    EXEC_LIMITED = 'limited_tender'
    EXEC_INQUIRY = 'price_inquiry'
    EXEC_CHOICES = [
        (EXEC_DIRECT, 'Direct Order'),
        (EXEC_TENDER, 'Public Tender'),
        (EXEC_LIMITED, 'Limited Tender'),
        (EXEC_INQUIRY, 'Price Inquiry'),
    ]

    ADMIN_LOCAL = 'local_purchasing'
    ADMIN_FOREIGN = 'foreign_purchasing'
    ADMIN_CHOICES = [
        (ADMIN_LOCAL, 'Local Purchasing'),
        (ADMIN_FOREIGN, 'Foreign Purchasing'),
    ]

    CURRENCY_CHOICES = [
        ('EGP', 'EGP - EGP'), ('USD', 'USD - $'), ('EUR', 'EUR - €'),
        ('SAR', 'SAR - ﷼'), ('AED', 'AED - د.إ'),
    ]

    rfq_no = models.CharField(max_length=20, unique=True, blank=True)
    year = models.PositiveIntegerField(default=2026)
    seq = models.PositiveIntegerField(default=0)

    title = models.CharField(max_length=300)
    technical_specs = models.TextField(blank=True)

    requesting_entity = models.CharField(max_length=200)
    requester_contact = models.CharField(max_length=150, blank=True)

    request_date = models.DateField(null=True, blank=True)
    administration = models.CharField(max_length=20, choices=ADMIN_CHOICES, default=ADMIN_LOCAL)
    execution_method = models.CharField(max_length=20, choices=EXEC_CHOICES, default=EXEC_DIRECT)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.PROTECT, related_name='rfqs')
    cost_center = models.ForeignKey(CostCenter, null=True, blank=True, on_delete=models.PROTECT, related_name='rfqs')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT, related_name='rfqs')
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.PROTECT, related_name='rfqs')

    estimated_value = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EGP')

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_NEW)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_rfqs')
    sap_no = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)

    REGION_CHOICES = [
        ('cairo', 'Cairo'), ('alexandria', 'Alexandria'), ('suez', 'Suez'),
        ('red_sea', 'Red Sea'), ('sinai', 'Sinai'), ('delta', 'Delta'), ('other', 'Other'),
    ]

    region = models.CharField(max_length=15, choices=REGION_CHOICES, blank=True)

    tender_issue_date = models.DateField(null=True, blank=True)
    technical_opening_date = models.DateField(null=True, blank=True)
    technical_report_date = models.DateField(null=True, blank=True)
    offers_to_requester_date = models.DateField(null=True, blank=True)
    financial_opening_date = models.DateField(null=True, blank=True)
    committee_presentation_date = models.DateField(null=True, blank=True)
    committee_approval_date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='rfqs_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-seq']
        permissions = []

    def __str__(self):
        return f"{self.rfq_no} · {self.title[:50]}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.rfq_no:
            if not self.year:
                self.year = (self.request_date or timezone.now().date()).year
            last = (RequestForQuotation.objects.filter(year=self.year)
                    .order_by('-seq').values_list('seq', flat=True).first())
            self.seq = (last or 0) + 1
            self.rfq_no = f"{self.year}-{self.seq:04d}"
        super().save(*args, **kwargs)
