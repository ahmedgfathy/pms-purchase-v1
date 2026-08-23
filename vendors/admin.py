from django.contrib import admin

from .models import ActivityProduct, Supplier, SupplierQualification, TaskMain, TaskSub, \
    TenderInvitation, VendorActivity, VendorOperation


@admin.register(TaskMain)
class TaskMainAdmin(admin.ModelAdmin):
    list_display = ('code', 'name_ar', 'name_en')
    search_fields = ('code', 'name_ar', 'name_en')


@admin.register(TaskSub)
class TaskSubAdmin(admin.ModelAdmin):
    list_display = ('code', 'main', 'name_ar', 'name_en')
    search_fields = ('code', 'name_ar', 'name_en')
    list_filter = ('main',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('supplier_no', 'name_ar', 'name_en', 'registration_status',
                    'certified', 'suspended', 'country')
    search_fields = ('supplier_no', 'name_ar', 'name_en')
    list_filter = ('registration_status', 'certified', 'suspended', 'struck_off', 'free_zone')


@admin.register(SupplierQualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'task_sub', 'registration_type', 'registration_capacity')
    search_fields = ('supplier__supplier_no',)


@admin.register(TenderInvitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('rfq', 'seq', 'supplier', 'progress_status',
                    'technical_result', 'po_status')
    search_fields = ('rfq__rfq_no', 'supplier__supplier_no')


@admin.register(ActivityProduct)
class ActivityProductAdmin(admin.ModelAdmin):
    list_display = ('activity_code', 'activity_name', 'main_name', 'product_code',
                    'product_service', 'product_status')
    search_fields = ('activity_code', 'activity_name', 'product_service', 'product_code')
    list_filter = ('product_status',)


@admin.register(VendorActivity)
class VendorActivityAdmin(admin.ModelAdmin):
    list_display = ('vendor_name_raw', 'activity_name', 'main_name', 'product_service',
                    'ptype', 'model')
    search_fields = ('vendor_name_raw', 'activity_name', 'product_service')
    list_filter = ('main_name',)


@admin.register(VendorOperation)
class VendorOperationAdmin(admin.ModelAdmin):
    list_display = ('operation_no', 'year', 'supplier', 'offer_status',
                    'technical_result', 'supply_status', 'po_status')
    search_fields = ('supplier__supplier_no',)
    list_filter = ('year',)
