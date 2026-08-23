from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from audit.models import record
from rbac import services
from rbac.decorators import module_required
from vendors.models import SupplierQualification, TaskMain, TaskSub, TenderInvitation

from .forms import RFQForm
from .models import RequestForQuotation


class RFQModuleMixin:
    module_code = 'rfq'
    action = 'view'

    def dispatch(self, request, *args, **kwargs):
        if not services.can(request.user, self.module_code, self.action):
            raise PermissionDenied(f"Missing '{self.action}' permission on module '{self.module_code}'")
        return super().dispatch(request, *args, **kwargs)


def apply_filters(qs, params):
    q = (params.get('q') or '').strip()
    status = params.get('status') or ''
    year = params.get('year') or ''
    admin = params.get('administration') or ''
    if q:
        qs = qs.filter(
            Q(rfq_no__icontains=q) | Q(title__icontains=q) |
            Q(requesting_entity__icontains=q) | Q(sap_no__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if year:
        qs = qs.filter(year=year)
    if admin:
        qs = qs.filter(administration=admin)
    return qs


@module_required('rfq', 'view')
def rfq_list(request):
    qs = apply_filters(RequestForQuotation.objects.select_related('project', 'client', 'location'), request.GET)
    years = sorted(set(RequestForQuotation.objects.values_list('year', flat=True)), reverse=True)
    return render(request, 'rfq/list.html', {
        'rfqs': qs[:200],
        'statuses': RequestForQuotation.STATUS_CHOICES,
        'admins': RequestForQuotation.ADMIN_CHOICES,
        'years': years,
        'filters': request.GET,
    })


@module_required('rfq', 'view')
def rfq_detail(request, pk):
    obj = get_object_or_404(RequestForQuotation.objects.select_related('project', 'client', 'location', 'cost_center', 'buyer'), pk=pk)
    transitions = [
        ('review', 'Under Review'),
        ('vendor_listing', 'Build Vendor List'),
        ('list_submitted', 'Submit List'),
        ('approved', 'Approve List'),
        ('rejected', 'Reject'),
        ('cancelled', 'Cancel'),
    ]
    return render(request, 'rfq/detail.html', {'rfq': obj, 'transitions': transitions})


@module_required('rfq', 'add')
def rfq_create(request):
    if request.method == 'POST':
        form = RFQForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, f'RFQ {obj.rfq_no} created.')
            return redirect('rfq_detail', pk=obj.pk)
    else:
        form = RFQForm(user=request.user)
    return render(request, 'rfq/form.html', {'form': form})


@module_required('rfq', 'change')
def rfq_update(request, pk):
    obj = get_object_or_404(RequestForQuotation, pk=pk)
    if request.method == 'POST':
        form = RFQForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'RFQ {obj.rfq_no} updated.')
            return redirect('rfq_detail', pk=obj.pk)
    else:
        form = RFQForm(instance=obj, user=request.user)
    return render(request, 'rfq/form.html', {'form': form, 'object': obj})


@module_required('rfq', 'change')
def rfq_set_status(request, pk, status):
    obj = get_object_or_404(RequestForQuotation, pk=pk)
    valid = dict(RequestForQuotation.STATUS_CHOICES)
    if request.method == 'POST' and status in valid and status != obj.status:
        old = obj.status
        obj.status = status
        obj.save()
        record('UPDATE', module='rfq', model_label='rfq.RequestForQuotation',
               object_id=obj.pk, object_repr=str(obj),
               changes={'status': {'old': old, 'new': status}})
        messages.success(request, f'RFQ {obj.rfq_no} → {valid[status]}.')
    return redirect('rfq_detail', pk=obj.pk)


@module_required('rfq', 'delete')
def rfq_delete(request, pk):
    obj = get_object_or_404(RequestForQuotation, pk=pk)
    if request.method == 'POST':
        no = obj.rfq_no
        obj.delete()
        messages.success(request, f'RFQ {no} deleted.')
        return redirect('rfq_list')
    return render(request, 'rfq/confirm_delete.html', {'rfq': obj})


INVITATION_FIELDS = {
    'progress_status', 'technical_result', 'technical_rejection_reason',
    'technical_compliance', 'certificates_status', 'initial_bond_type',
    'initial_bond_status', 'final_bond_status', 'supply_status', 'po_status', 'notes',
}


def _get_invitation(rfq, inv_pk):
    return get_object_or_404(TenderInvitation.objects.select_related('supplier'), rfq=rfq, pk=inv_pk)


@module_required('rfq', 'change')
def vendor_pick(request, pk):
    """v2026 'Form.Vendor Select' — build the tender vendor list from qualified vendors."""
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    main = request.GET.get('main') or ''
    sub = request.GET.get('sub') or ''
    subs = TaskSub.objects.select_related('main')
    if main:
        subs = subs.filter(main_id=main)

    quals = None
    invited_ids = set(rfq.invitations.values_list('supplier_id', flat=True))
    if sub:
        quals = (SupplierQualification.objects.filter(task_sub_id=sub)
                 .exclude(supplier_id__in=invited_ids)
                 .select_related('supplier', 'task_sub'))

    if request.method == 'POST':
        ids = request.POST.getlist('suppliers')
        next_seq = rfq.invitations.count() + 1
        added = 0
        for sid in ids:
            _, created = TenderInvitation.objects.get_or_create(
                rfq=rfq, supplier_id=sid, defaults={'seq': next_seq})
            if created:
                next_seq += 1
                added += 1
        messages.success(request, f'{added} vendor(s) added to RFQ {rfq.rfq_no} list.')
        return redirect('rfq_vendor_list', pk=pk)

    return render(request, 'rfq/vendor_pick.html', {
        'rfq': rfq,
        'mains': TaskMain.objects.all(),
        'subs': subs,
        'selected_main': main,
        'selected_sub': sub,
        'results': quals,
        'invited_count': len(invited_ids),
    })


@module_required('rfq', 'view')
def vendor_list_manage(request, pk):
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    return render(request, 'rfq/vendor_list.html', {
        'rfq': rfq,
        'invitations': (rfq.invitations.select_related('supplier')
                        .select_related('rfq')),
        'gen_statuses': TenderInvitation.GEN_STATUS_CHOICES,
        'bond_types': TenderInvitation.BOND_CHOICES,
        'tech_results': TenderInvitation.TECH_RESULT_CHOICES,
        'can_edit': request.user.is_superuser or services.can(request.user, 'rfq', 'change'),
    })


@module_required('rfq', 'view')
def vendor_list_print(request, pk):
    rfq = get_object_or_404(RequestForQuotation.objects.select_related('client', 'project'), pk=pk)
    lang = request.GET.get('lang', 'E').upper()
    return render(request, 'rfq/vendorlist_print.html', {
        'rfq': rfq,
        'invitations': rfq.invitations.select_related('supplier'),
        'arabic': lang == 'A',
    })


@module_required('rfq', 'change')
def invitation_update(request, pk, inv_pk):
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    inv = _get_invitation(rfq, inv_pk)
    if request.method == 'POST':
        changes = {}
        for f in INVITATION_FIELDS:
            val = request.POST.get(f)
            if val is None:
                continue
            cur = getattr(inv, f)
            if f == 'technical_compliance':
                val = val in ('on', 'true', 'True', '1')
            if str(cur) != str(val) and val != '':
                changes[f] = {'old': str(cur), 'new': str(val)}
                setattr(inv, f, val)
        if changes:
            inv.save()
            record('UPDATE', module='rfq', model_label='vendors.TenderInvitation',
                   object_id=inv.pk, object_repr=f'RFQ {rfq.rfq_no} ← {inv.supplier}',
                   changes=changes)
        messages.success(request, 'Vendor entry updated.')
    return redirect('rfq_vendor_list', pk=pk)


@module_required('rfq', 'delete')
def invitation_delete(request, pk, inv_pk):
    rfq = get_object_or_404(RequestForQuotation, pk=pk)
    inv = _get_invitation(rfq, inv_pk)
    if request.method == 'POST':
        repr_ = str(inv)
        inv.delete()
        record('DELETE', module='rfq', model_label='vendors.TenderInvitation',
               object_id=inv_pk, object_repr=repr_, changes=None)
        messages.success(request, 'Vendor removed from list.')
    return redirect('rfq_vendor_list', pk=pk)
