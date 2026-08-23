from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect, render

from rbac.services import is_admin, visible_modules
from rfq.models import RequestForQuotation
from vendors.models import Supplier, TenderInvitation
from tenders.models import PurchaseOrder


@login_required
def dashboard(request):
    modules = visible_modules(request.user)
    module_urls = {
        'rfq': '/rfq/',
        'purchases': '/purchases/',
        'suppliers': '/vendors/',
        'tender': '/tenders/',
        'administration': '/admin/',
        'audit_trail': '/admin/audit/auditlog/',
    }
    tiles = []
    for m in modules:
        url = module_urls.get(m.code)
        if not url:
            continue
        if m.code in ('administration', 'audit_trail') and not is_admin(request.user):
            continue
        tiles.append({'code': m.code, 'name': m.name, 'url': url})

    # --- tender statistics ---
    qs = RequestForQuotation.objects.all()
    total = qs.count()
    status_counts = {}
    for s, _ in RequestForQuotation.STATUS_CHOICES:
        status_counts[s] = qs.filter(status=s).count()
    region_counts = {}
    for r, _ in RequestForQuotation.REGION_CHOICES:
        region_counts[r] = qs.filter(region=r).count()
    method_counts = {}
    for m, _ in RequestForQuotation.EXEC_CHOICES:
        method_counts[m] = qs.filter(execution_method=m).count()

    total_value = qs.aggregate(s=Sum('estimated_value'))['s'] or 0
    total_suppliers = Supplier.objects.count()
    total_invitations = TenderInvitation.objects.count()
    total_pos = PurchaseOrder.objects.count()
    invited_vendors = TenderInvitation.objects.values('supplier').distinct().count()

    # region value
    region_values = {}
    for r, _ in RequestForQuotation.REGION_CHOICES:
        region_values[r] = qs.filter(region=r).aggregate(s=Sum('estimated_value'))['s'] or 0

    # region × status (for stacked / grouped display)
    region_status = {}
    for r, _ in RequestForQuotation.REGION_CHOICES:
        region_status[r] = {}
        for s, _ in RequestForQuotation.STATUS_CHOICES:
            region_status[r][s] = qs.filter(region=r, status=s).count()

    # --- pre-computed chart data ---
    approved_count = status_counts.get('approved', 0)

    COLOR = {
        'new': '#58b0ff', 'approved': '#34c759', 'vendor_listing': '#ff9500',
        'review': '#5ac8fa', 'list_submitted': '#ffcc00', 'rejected': '#af52de',
        'cancelled': '#ff3b30',
        'cairo': '#58b0ff', 'alexandria': '#34c759',
        'direct_order': '#ff9500', 'limited_tender': '#58b0ff',
        'public_tender': '#34c759', 'price_inquiry': '#af52de',
    }

    # status donut (cumulative percentages)
    status_data = []
    cum = 0
    for s, label in RequestForQuotation.STATUS_CHOICES:
        c = status_counts.get(s, 0)
        pct = (c / total * 100) if total else 0
        status_data.append({
            'key': s, 'label': label, 'count': c, 'pct': round(pct, 1),
            'start': cum, 'color': COLOR.get(s, '#6b7a8d'),
        })
        cum += pct

    region_data = []
    for r, label in RequestForQuotation.REGION_CHOICES:
        c = region_counts.get(r, 0)
        if c:
            region_data.append({'key': r, 'label': label, 'count': c, 'color': COLOR.get(r)})

    method_data = []
    for m, label in RequestForQuotation.EXEC_CHOICES:
        c = method_counts.get(m, 0)
        if c:
            method_data.append({'key': m, 'label': label, 'count': c, 'color': COLOR.get(m)})

    region_max = max([c for c in region_counts.values()] + [1])
    method_max = max([c for c in method_counts.values()] + [1])

    ctx = {
        'tiles': tiles,
        'total': total,
        'total_value': total_value,
        'total_suppliers': total_suppliers,
        'total_invitations': total_invitations,
        'total_pos': total_pos,
        'invited_vendors': invited_vendors,
        'approved_count': approved_count,
        'status_data': status_data,
        'region_data': region_data,
        'method_data': method_data,
        'region_max': region_max,
        'method_max': method_max,
        'region_values': region_values,
        'region_status': region_status,
        'RequestForQuotation': RequestForQuotation,
    }
    return render(request, 'dashboard.html', ctx)


@login_required
def permission_denied(request, exception=None):
    return render(request, '403.html', status=403)


def set_lang(request, lang):
    if lang in ('en', 'ar'):
        request.session['app_lang'] = lang
    nxt = request.POST.get('next') or request.GET.get('next') or '/'
    from django.utils.http import url_has_allowed_host_and_scheme
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = '/'
    return redirect(nxt)
