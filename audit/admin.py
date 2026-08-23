from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor_name', 'action', 'module', 'model_label', 'object_id', 'object_repr', 'ip_address', 'status_code')
    list_filter = ('action', 'module', 'model_label')
    search_fields = ('actor_name', 'object_repr', 'object_id', 'path')
    date_hierarchy = 'timestamp'
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
