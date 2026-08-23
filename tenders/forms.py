from django import forms

from rbac.forms import RestrictedModelForm
from rfq.models import RequestForQuotation

from .models import PurchaseOrder


class PurchaseOrderForm(RestrictedModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'rfq', 'legacy_op_no', 'supplier', 'po_no', 'po_date', 'year',
            'items_description', 'value', 'currency', 'payment_method',
            'cheque_no', 'cheque_date',
            'lc_open_date', 'lc_receipt_date', 'bank_name', 'amount_egp', 'amount_usd',
            'delivery_days', 'delivery_start_date', 'expected_delivery_date',
            'actual_delivery_date', 'delivery_place', 'shipping_method',
            'goods_receipt_no', 'shipping_docs_date', 'customs_clearance_date',
            'disbursement_request_date', 'bond_refund_date',
            'followup_by', 'sap_no', 'notes', 'po_image',
            'items_delivered', 'qty_delivered', 'on_time', 'right_place',
            'per_specs', 'po_form_complete', 'docs_complete',
        ]
        widgets = {
            'po_date': forms.DateInput(attrs={'type': 'date'}),
            'cheque_date': forms.DateInput(attrs={'type': 'date'}),
            'lc_open_date': forms.DateInput(attrs={'type': 'date'}),
            'lc_receipt_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_start_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'shipping_docs_date': forms.DateInput(attrs={'type': 'date'}),
            'customs_clearance_date': forms.DateInput(attrs={'type': 'date'}),
            'disbursement_request_date': forms.DateInput(attrs={'type': 'date'}),
            'bond_refund_date': forms.DateInput(attrs={'type': 'date'}),
            'items_description': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class MilestoneDatesForm(forms.ModelForm):
    """Tender milestone dates from legacy Oprations table."""

    class Meta:
        model = RequestForQuotation
        fields = [
            'region', 'tender_issue_date', 'technical_opening_date',
            'technical_report_date', 'offers_to_requester_date',
            'financial_opening_date', 'committee_presentation_date',
            'committee_approval_date',
        ]
        widgets = {f: forms.DateInput(attrs={'type': 'date'}) for f in [
            'tender_issue_date', 'technical_opening_date', 'technical_report_date',
            'offers_to_requester_date', 'financial_opening_date',
            'committee_presentation_date', 'committee_approval_date']}
