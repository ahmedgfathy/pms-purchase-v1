from .models import AppModule, FieldPermission, ModulePermission, Role

ACTION_FLAG = {
    'view': 'can_view',
    'add': 'can_add',
    'change': 'can_change',
    'delete': 'can_delete',
}


def user_roles(user):
    if not getattr(user, 'is_authenticated', False):
        return Role.objects.none()
    return Role.objects.filter(user_assignments__user=user)


def is_admin(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    return user_roles(user).filter(can_manage_rbac=True).exists()


def can(user, module_code, action='view'):
    if not getattr(user, 'is_authenticated', False):
        return False
    flag = ACTION_FLAG.get(action)
    if flag is None:
        raise ValueError(f"Unknown action: {action}")
    if is_admin(user):
        return True
    if not AppModule.objects.filter(code=module_code, is_active=True).exists():
        return False
    return ModulePermission.objects.filter(
        role__in=user_roles(user), module__code=module_code
    ).filter(**{flag: True}).exists()


def visible_modules(user):
    if not getattr(user, 'is_authenticated', False):
        return AppModule.objects.none()
    qs = AppModule.objects.filter(is_active=True)
    if is_admin(user):
        return qs
    return qs.filter(role_permissions__role__in=user_roles(user), role_permissions__can_view=True).distinct()


def field_mode_map(user, model_label):
    modes = {}
    if not getattr(user, 'is_authenticated', False):
        return modes
    if is_admin(user):
        return modes
    severity = {FieldPermission.EDITABLE: 0, FieldPermission.READONLY: 1, FieldPermission.HIDDEN: 2}
    for perm in FieldPermission.objects.filter(model_label=model_label, role__in=user_roles(user)):
        current = modes.get(perm.field_name)
        if current is None or severity[perm.mode] > severity[current]:
            modes[perm.field_name] = perm.mode
    return modes


def field_mode(user, model_label, field_name):
    return field_mode_map(user, model_label).get(field_name, FieldPermission.EDITABLE)
