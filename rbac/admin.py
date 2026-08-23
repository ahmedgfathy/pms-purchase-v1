from django.contrib import admin

from .models import AppModule, FieldPermission, ModulePermission, Role, UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'can_manage_rbac', 'is_system')
    search_fields = ('name', 'code')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_by', 'assigned_at')
    autocomplete_fields = ('user', 'role')
    list_filter = ('role',)


@admin.register(AppModule)
class AppModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_editable = ('is_active',)


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'module', 'can_view', 'can_add', 'can_change', 'can_delete')
    list_filter = ('role', 'module')
    list_editable = ('can_view', 'can_add', 'can_change', 'can_delete')


@admin.register(FieldPermission)
class FieldPermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'model_label', 'field_name', 'mode')
    list_filter = ('role', 'mode')
    search_fields = ('model_label', 'field_name')
