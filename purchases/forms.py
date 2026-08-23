from django import forms

from rbac.forms import RestrictedModelForm

from .models import PurchaseRequest


class PurchaseRequestForm(RestrictedModelForm):

    class Meta:
        model = PurchaseRequest
        fields = ['title', 'description', 'quantity', 'unit_price', 'currency', 'budget_code', 'needed_by']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'needed_by': forms.DateInput(attrs={'type': 'date'}),
        }
