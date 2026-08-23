from django.contrib import admin

from .models import PurchaseOrder


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_no', 'po_date', 'supplier', 'rfq', 'value', 'currency',
                    'sap_no', 'checklist_done')
    search_fields = ('po_no', 'sap_no', 'legacy_op_no', 'supplier__name_ar')
    list_filter = ('year', 'currency', 'payment_method')
