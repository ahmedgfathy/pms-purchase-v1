import django.forms as forms

from rbac.forms import RestrictedModelForm

from .models import RequestForQuotation


class RFQForm(RestrictedModelForm):

    class Meta:
        model = RequestForQuotation
        fields = [
            'title', 'technical_specs', 'requesting_entity', 'requester_contact',
            'request_date', 'administration', 'execution_method',
            'location', 'cost_center', 'project', 'client',
            'estimated_value', 'currency', 'buyer', 'sap_no', 'notes',
        ]
        widgets = {
            'technical_specs': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'request_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', '')
