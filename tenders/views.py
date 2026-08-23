from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
import urllib.parse

from audit.models import record
from rbac import services
from rbac.decorators import module_required
from rfq.models import RequestForQuotation
from vendors.models import TenderInvitation

from .forms import MilestoneDatesForm, PurchaseOrderForm
from .models import PurchaseOrder


EVAL_FIELDS = {
    'offer_status', 'technical_result', 'technical_rejection_reason',
    'technical_compliance', 'certificates_status', 'initial_bond_type',
    'initial_bond_status', 'final_bond_status', 'late_penalty',
    'financial_offer', 'financial_currency', 'notes',
}


def _get_rfq_list(filters=None):
    """Ordered queryset for nav, respecting filters."""
    qs = RequestForQuotation.objects.all()
    if filters:
        if filters.get('year'):
            qs = qs.filter(year=filters['year'])
        if filters.get('method'):
            qs = qs.filter(execution_method=filters['method'])
        if filters.get('region'):
            qs = qs.filter(region=filters['region'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
    return list(qs.order_by('-year', '-seq').values_list('pk', flat=True))


@module_required('tender', 'view')
def tender_detail(request):
    """Single tender detail view with prev/next navigation and search."""
    q = (request.GET.get('q') or '').strip()
    pk = request.GET.get('pk')
    year = request.GET.get('year') or ''
    method = request.GET.get('method') or ''
    region = request.GET.get('region') or ''
    status = request.GET.get('status') or ''

    filters = {}
    if year:
        filters['year'] = year
    if method:
        filters['method'] = method
    if region:
        filters['region'] = region
    if status:
        filters['status'] = status

    rfq = None
    if q:
        rfq = RequestForQuotation.objects.filter(
            Q(rfq_no__icontains=q) | Q(seq__icontains=q)
        ).select_related('client', 'project', 'location', 'cost_center').first()
        if rfq:
            params = urllib.parse.urlencode({'pk': rfq.pk, **filters})
            return redirect(f'/tenders/?{params}')
    elif pk:
        rfq = get_object_or_404(
            RequestForQuotation.objects.select_related(
                'client', 'project', 'location', 'cost_center'), pk=pk)
    else:
        filtered_ids = _get_rfq_list(filters)
        if filtered_ids:
            params = urllib.parse.urlencode({'pk': filtered_ids[0], **filters})
            return redirect(f'/tenders/?{params}')

    if not rfq:
        return render(request, 'tenders/tender_detail.html', {
            'rfq': None, 'filters': filters,
            'years': [], 'statuses': [], 'methods': [], 'regions': [],
        })

    # Nav: prev/next (respect filters)
    all_ids = _get_rfq_list(filters)
    total_count = len(all_ids)
    try:
        idx = all_ids.index(rfq.pk)
    except ValueError:
        idx = 0
    prev_pk = all_ids[idx + 1] if idx + 1 < len(all_ids) else None
    next_pk = all_ids[idx - 1] if idx > 0 else None

    invitations = rfq.invitations.select_related('supplier').order_by('seq')
    can_edit = request.user.is_superuser or services.can(request.user, 'tender', 'change')

    from rfq.models import RequestForQuotation as RFQ
    years = sorted(RFQ.objects.values_list('year', flat=True).distinct(), reverse=True)
    return render(request, 'tenders/tender_detail.html', {
        'rfq': rfq,
        'prev_pk': prev_pk,
        'next_pk': next_pk,
        'nav_idx': idx,
        'nav_total': total_count,
        'inv_count': invitations.count(),
        'invitations': invitations[:50],
        'milestone_form': MilestoneDatesForm(instance=rfq),
        'can_edit': can_edit,
        'filters': filters,
        'years': years,
        'statuses': RFQ.STATUS_CHOICES,
        'methods': RFQ.EXEC_CHOICES,
        'regions': RFQ.REGION_CHOICES,
    })


@module_required('tender', 'view')
def po_list(request):
    qs = PurchaseOrder.objects.select_related('rfq', 'supplier')
    q = (request.GET.get('q') or '').strip()
    year = request.GET.get('year') or ''
    if q:
        qs = qs.filter(Q(po_no__icontains=q) | Q(sap_no__icontains=q) |
                       Q(supplier__name_ar__icontains=q) | Q(supplier__name_en__icontains=q))
    if year:
        qs = qs.filter(year=year)
    years = sorted(set(PurchaseOrder.objects.values_list('year', flat=True)), reverse=True)
    return render(request, 'tenders/po_list.html', {'pos': qs[:200], 'years': years, 'filters': request.GET})


@module_required('tender', 'view')
def po_detail(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.select_related('rfq', 'supplier'), pk=pk)
    checklist_items = [(label, getattr(po, f)) for f, label in PurchaseOrder.CHECKLIST_FIELDS]
    return render(request, 'tenders/po_detail.html', {'po': po, 'checklist_items': checklist_items})


@module_required('tender', 'add')
def po_create(request):
    rfq = None
    initial = {'year': 2026}
    if request.GET.get('rfq'):
        rfq = get_object_or_404(RequestForQuotation, pk=request.GET['rfq'])
        initial['rfq'] = rfq
        if request.GET.get('supplier'):
            initial['supplier'] = request.GET['supplier']
        elif rfq.invitations.filter(rank=1).exists():
            initial['supplier'] = rfq.invitations.get(rank=1).supplier_id
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, request.FILES)
        if form.is_valid():
            po = form.save()
            messages.success(request, f'PO {po.po_no} created.')
            return redirect('po_detail', pk=po.pk)
    else:
        form = PurchaseOrderForm(initial=initial)
    return render(request, 'tenders/po_form.html', {'form': form})


@module_required('tender', 'change')
def po_update(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, request.FILES, instance=po)
        if form.is_valid():
            form.save()
            messages.success(request, f'PO {po.po_no} updated.')
            return redirect('po_detail', pk=pk)
    else:
        form = PurchaseOrderForm(instance=po)
    return render(request, 'tenders/po_form.html', {'form': form, 'object': po})


@module_required('tender', 'delete')
def po_delete(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        no = po.po_no
        po.delete()
        messages.success(request, f'PO {no} deleted.')
        return redirect('po_list')
    return render(request, 'tenders/po_confirm_delete.html', {'po': po})


@module_required('tender', 'view')
def po_print(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.select_related('rfq', 'supplier'), pk=pk)
    arabic = request.GET.get('lang', 'A').upper() == 'A'
    return render(request, 'tenders/po_print.html', {'po': po, 'arabic': arabic})


# ---------- evaluation board ----------

def _rfq(rfq_pk):
    from rfq.models import RequestForQuotation
    return get_object_or_404(RequestForQuotation.objects.select_related(
        'client', 'project', 'location', 'cost_center'), pk=rfq_pk)


@module_required('tender', 'view')
def evaluation_board(request, rfq_pk):
    rfq = _rfq(rfq_pk)
    return render(request, 'tenders/evaluation.html', {
        'rfq': rfq,
        'invitations': (rfq.invitations.select_related('supplier')
                        .order_by('seq')),
        'offer_statuses': TenderInvitation.OFFER_STATUS_CHOICES,
        'tech_results': TenderInvitation.TECH_RESULT_CHOICES,
        'gen_statuses': TenderInvitation.GEN_STATUS_CHOICES,
        'bond_types': TenderInvitation.BOND_CHOICES,
        'penalties': TenderInvitation.PENALTY_CHOICES,
        'currencies': [('EGP', 'EGP'), ('USD', 'USD'), ('EUR', 'EUR')],
        'milestone_form': MilestoneDatesForm(instance=rfq),
        'can_edit': request.user.is_superuser or services.can(request.user, 'tender', 'change'),
    })


@module_required('tender', 'change')
def invitation_evaluate(request, rfq_pk, inv_pk):
    rfq = _rfq(rfq_pk)
    inv = get_object_or_404(TenderInvitation, rfq=rfq, pk=inv_pk)
    if request.method == 'POST':
        changes = {}
        for f in EVAL_FIELDS:
            val = request.POST.get(f)
            if val is None:
                continue
            cur = getattr(inv, f)
            if f == 'technical_compliance':
                val = val in ('on', 'true', 'True', '1')
            if str(cur) != str(val) and (val != '' or f in ('financial_offer',)):
                changes[f] = {'old': str(cur), 'new': str(val)}
                setattr(inv, f, val)
        if changes:
            inv.save()
            record('UPDATE', module='tender', model_label='vendors.TenderInvitation',
                   object_id=inv.pk, object_repr=f'RFQ {rfq.rfq_no} ← {inv.supplier}',
                   changes=changes)
            messages.success(request, 'Evaluation saved.')
    return redirect('evaluation_board', rfq_pk=rfq_pk)


@module_required('tender', 'change')
def save_milestones(request, rfq_pk):
    rfq = _rfq(rfq_pk)
    if request.method == 'POST':
        form = MilestoneDatesForm(request.POST, instance=rfq)
        if form.is_valid():
            form.save()
            record('UPDATE', module='tender', model_label='rfq.RequestForQuotation',
                   object_id=rfq.pk, object_repr=str(rfq),
                   changes={k: {'new': str(v)} for k, v in form.cleaned_data.items()})
            messages.success(request, 'Tender milestones saved.')
    return redirect('evaluation_board', rfq_pk=rfq_pk)


@module_required('tender', 'change')
def rank_offers(request, rfq_pk):
    """Financial ranking: lowest compliant offer ranks first."""
    rfq = _rfq(rfq_pk)
    if request.method == 'POST':
        eligible = (rfq.invitations
                    .filter(technical_result__in=('passed',), offer_status='submitted')
                    .exclude(financial_offer=None)
                    .order_by('financial_offer'))
        prev_rank = 0
        prev_val = None
        for i, inv in enumerate(eligible, start=1):
            rank = prev_rank if inv.financial_offer == prev_val else i
            inv.rank = rank
            inv.save(update_fields=['rank'])
            prev_rank, prev_val = rank, inv.financial_offer
        rfq.invitations.exclude(pk__in=[i.pk for i in eligible]).update(rank=None)
        record('UPDATE', module='tender', model_label='rfq.RequestForQuotation',
               object_id=rfq.pk, object_repr=str(rfq),
               changes={'ranking': {'new': f'{eligible.count()} offers ranked'}})
        messages.success(request, f'Ranked {eligible.count()} compliant financial offers.')
    return redirect('evaluation_board', rfq_pk=rfq_pk)


@module_required('tender', 'change')
def award(request, rfq_pk, inv_pk):
    rfq = _rfq(rfq_pk)
    inv = get_object_or_404(TenderInvitation, rfq=rfq, pk=inv_pk)
    if request.method == 'POST':
        old_ranks = list(rfq.invitations.exclude(rank=None).values_list('pk', 'rank'))
        rfq.invitations.update(rank=None)
        inv.rank = 1
        inv.save(update_fields=['rank'])
        if rfq.status != 'approved':
            old = rfq.status
            rfq.status = 'approved'
            rfq.save()
            record('UPDATE', module='rfq', model_label='rfq.RequestForQuotation',
                   object_id=rfq.pk, object_repr=str(rfq),
                   changes={'status': {'old': old, 'new': 'approved'}})
        record('UPDATE', module='tender', model_label='vendors.TenderInvitation',
               object_id=inv.pk, object_repr=f'RFQ {rfq.rfq_no} ← {inv.supplier}',
               changes={'awarded': {'old': str(old_ranks), 'new': str(inv.supplier.supplier_no)}})
        messages.success(request, f'Awarded to {inv.supplier}. Create the PO next.')
    return redirect('evaluation_board', rfq_pk=rfq_pk)
