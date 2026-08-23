from django.core.exceptions import PermissionDenied

from . import services


def module_required(module_code, action='view'):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not services.can(request.user, module_code, action):
                raise PermissionDenied(f"Missing '{action}' permission on module '{module_code}'")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
