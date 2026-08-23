from django.conf import settings
from django.db import models

from .context import current_context


class AuditLog(models.Model):
    LOGIN = 'LOGIN'
    LOGIN_FAILED = 'LOGIN_FAILED'
    LOGOUT = 'LOGOUT'
    VIEW = 'VIEW'
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    DENIED = 'DENIED'
    ACTION_CHOICES = [
        (LOGIN, LOGIN), (LOGIN_FAILED, LOGIN_FAILED), (LOGOUT, LOGOUT),
        (VIEW, VIEW), (CREATE, CREATE), (UPDATE, UPDATE), (DELETE, DELETE),
        (DENIED, DENIED),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_entries')
    actor_name = models.CharField(max_length=150, blank=True)

    action = models.CharField(max_length=15, choices=ACTION_CHOICES, db_index=True)
    module = models.CharField(max_length=50, blank=True, db_index=True)
    model_label = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=100, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(null=True, blank=True)

    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=500, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.actor_name or '-'} {self.action} {self.model_label} {self.object_id}"


def record(action, *, actor=None, module='', model_label='', object_id='', object_repr='',
           changes=None, status_code=None, duration_ms=None):
    ctx = current_context()
    user = actor or ctx['user']
    AuditLog.objects.create(
        actor=user,
        actor_name=user.username if user else '',
        action=action,
        module=module,
        model_label=model_label,
        object_id=str(object_id) if object_id != '' else '',
        object_repr=str(object_repr)[:255] if object_repr else '',
        changes=changes,
        method=ctx['method'],
        path=ctx['path'],
        status_code=status_code,
        ip_address=ctx['ip'],
        user_agent=ctx['ua'],
        duration_ms=duration_ms,
    )


class AuditedModel(models.Model):
    class Meta:
        abstract = True

    def _audit_diff(self, old):
        changes = {}
        for field in self._meta.concrete_fields:
            name = field.name
            if getattr(field, 'auto_now_add', False) or getattr(field, 'auto_now', False):
                continue
            new_val = field.value_from_object(self)
            old_val = field.value_from_object(old) if old is not None else None
            if old is None and new_val in (None, ''):
                continue
            if str(old_val) != str(new_val):
                changes[name] = {'old': None if old is None else str(old_val), 'new': str(new_val)}
        return changes

    def save(self, *args, **kwargs):
        creating = self.pk is None
        old = None
        if not creating:
            try:
                old = type(self).objects.get(pk=self.pk)
            except type(self).DoesNotExist:
                creating = True
        super().save(*args, **kwargs)
        label = self._meta.label
        if creating:
            record('CREATE', model_label=label, module=label.split('.')[0], object_id=self.pk, object_repr=str(self),
                   changes=self._audit_diff(None))
        else:
            diff = self._audit_diff(old)
            if diff:
                record('UPDATE', model_label=label, module=label.split('.')[0], object_id=self.pk, object_repr=str(self), changes=diff)

    def delete(self, *args, **kwargs):
        snapshot = {f.name: str(f.value_from_object(self)) for f in self._meta.concrete_fields
                    if not getattr(f, 'auto_now', False)}
        label = self._meta.label
        pk, repr_ = self.pk, str(self)
        super().delete(*args, **kwargs)
        record('DELETE', model_label=label, module=label.split('.')[0], object_id=pk, object_repr=repr_, changes=snapshot)
