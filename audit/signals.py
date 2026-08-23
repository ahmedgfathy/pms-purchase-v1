from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import record


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    record('LOGIN', actor=user, module='auth', model_label='auth.User', object_id=user.pk, object_repr=f"Login: {user.username}")


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user and user.is_authenticated:
        record('LOGOUT', actor=user, module='auth', model_label='auth.User', object_id=user.pk, object_repr=f"Logout: {user.username}")


@receiver(user_login_failed)
def on_login_failed(sender, credentials, **kwargs):
    username = credentials.get('username', '')
    record('LOGIN_FAILED', actor=None, module='auth', object_repr=f"Failed login attempt: {username}")
