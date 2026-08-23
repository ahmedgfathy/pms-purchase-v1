from django.conf import settings
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    can_manage_rbac = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rbac_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'role')]

    def __str__(self):
        return f"{self.user.username} → {self.role.name}"


class AppModule(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ModulePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='module_permissions')
    module = models.ForeignKey(AppModule, on_delete=models.CASCADE, related_name='role_permissions')

    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_change = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = [('role', 'module')]

    def __str__(self):
        return f"{self.role.code} × {self.module.code}"


class FieldPermission(models.Model):
    HIDDEN = 'hidden'
    READONLY = 'readonly'
    EDITABLE = 'editable'
    MODE_CHOICES = [
        (HIDDEN, 'Hidden'),
        (READONLY, 'View only'),
        (EDITABLE, 'Editable'),
    ]

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='field_permissions')
    model_label = models.CharField(max_length=100, help_text="app.Model e.g. purchases.PurchaseRequest")
    field_name = models.CharField(max_length=100)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=EDITABLE)

    class Meta:
        unique_together = [('role', 'model_label', 'field_name')]

    def __str__(self):
        return f"{self.role.code} × {self.model_label}.{self.field_name} → {self.mode}"
