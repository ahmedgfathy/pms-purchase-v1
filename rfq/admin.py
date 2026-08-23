from django.contrib import admin

from .models import Client, CostCenter, Location, Project, RequestForQuotation


@admin.register(RequestForQuotation)
class RFQAdmin(admin.ModelAdmin):
    list_display = ('rfq_no', 'title', 'requesting_entity', 'status', 'administration', 'estimated_value', 'currency', 'buyer')
    list_filter = ('status', 'administration', 'year')
    search_fields = ('rfq_no', 'title', 'requesting_entity', 'sap_no')


admin.site.register(Client)
admin.site.register(CostCenter)
admin.site.register(Location)
admin.site.register(Project)
