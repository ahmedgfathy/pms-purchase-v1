from django import forms

from rbac.forms import RestrictedModelForm

from .models import Supplier, SupplierQualification


class SupplierForm(RestrictedModelForm):
    class Meta:
        model = Supplier
        fields = [
            'supplier_no', 'name_ar', 'name_en', 'registration_status',
            'registered_local', 'registered_foreign', 'suspended', 'struck_off',
            'dossier_no', 'dossier_type', 'committee_no', 'committee_date',
            'commercial_registry_no', 'commercial_registry_expiry',
            'tax_card_no', 'tax_card_expiry', 'vat_no', 'vat_expiry',
            'capital_amount', 'capital_currency',
            'country', 'address', 'phone1', 'phone2', 'mobile1', 'mobile2', 'fax',
            'email1', 'email2', 'website', 'contact_person', 'owner_name',
            'agent_name', 'agent_phone', 'agent_mobile', 'agent_fax',
            'agent_email', 'agent_address', 'agency_documents',
            'category', 'free_zone', 'certified', 'previous_no',
            'notes', 'private_notes',
        ]
        widgets = {
            'committee_date': forms.DateInput(attrs={'type': 'date'}),
            'commercial_registry_expiry': forms.DateInput(attrs={'type': 'date'}),
            'tax_card_expiry': forms.DateInput(attrs={'type': 'date'}),
            'vat_expiry': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'agent_address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'private_notes': forms.Textarea(attrs={'rows': 2}),
        }


class QualificationForm(forms.ModelForm):
    class Meta:
        model = SupplierQualification
        fields = ['task_sub', 'registration_type', 'registration_capacity', 'brand', 'original_maker', 'origin_country', 'notes']
