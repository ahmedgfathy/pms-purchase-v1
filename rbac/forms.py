from django import forms

from . import services
from .models import FieldPermission


class RestrictedModelForm(forms.ModelForm):

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_modes = {}
        self._restricted = set()
        if user is not None and self._meta.model is not None:
            self.field_modes = services.field_mode_map(user, self._meta.model._meta.label)
            for name, mode in self.field_modes.items():
                if name in self.fields:
                    f = self.fields[name]
                    if mode == FieldPermission.HIDDEN:
                        f.widget = forms.HiddenInput()
                        f.required = False
                        self._restricted.add(name)
                    elif mode == FieldPermission.READONLY:
                        f.disabled = True
                        f.required = False
                        self._restricted.add(name)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        for name in self._restricted:
            if instance is not None and instance.pk and name in cleaned:
                cleaned[name] = getattr(instance, name, None)
            elif instance is None or not instance.pk:
                cleaned.pop(name, None)
        return cleaned
