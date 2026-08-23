from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from audit.models import record
from rbac.decorators import module_required

from .forms import QualificationForm, SupplierForm
from .models import ActivityProduct, Supplier, SupplierQualification, TaskMain, TaskSub, \
    VendorActivity, VendorOperation


@module_required('suppliers', 'view')
def vendor_list(request):
    qs = Supplier.objects.all()
    q = (request.GET.get('q') or '').strip()
    status = request.GET.get('status') or ''
    country = request.GET.get('country') or ''
    certified = request.GET.get('certified') or ''
    flag = request.GET.get('flag') or ''
    if q:
        qs = qs.filter(Q(supplier_no__icontains=q) | Q(name_ar__icontains=q) | Q(name_en__icontains=q))
    if status:
        qs = qs.filter(registration_status=status)
    if country:
        qs = qs.filter(country__iexact=country)
    if certified == 'yes':
        qs = qs.filter(certified=True)
    elif certified == 'no':
        qs = qs.filter(certified=False)
    if flag == 'suspended':
        qs = qs.filter(suspended=True)
    elif flag == 'struck_off':
        qs = qs.filter(struck_off=True)
    elif flag == 'free_zone':
        qs = qs.filter(free_zone=True)

    page = Paginator(qs.order_by('supplier_no'), 50).get_page(request.GET.get('page'))
    return render(request, 'vendors/list.html', {
        'page': page,
        'total': qs.count(),
        'statuses': Supplier.REG_STATUS_CHOICES,
        'countries': Supplier.objects.exclude(country='').values_list('country', flat=True).distinct().order_by('country'),
        'filters': request.GET,
    })


@module_required('suppliers', 'view')
def vendor_detail(request, pk):
    obj = get_object_or_404(Supplier, pk=pk)
    quals = (SupplierQualification.objects.filter(supplier=obj)
             .select_related('task_sub', 'task_sub__main').order_by('task_sub__code'))
    invites = obj.invitations.select_related('rfq').order_by('-rfq__year', '-rfq__seq')[:50]
    activities = VendorActivity.objects.filter(supplier=obj).order_by('activity_name')
    name_activities = (VendorActivity.objects.filter(supplier=None, vendor_name_raw=obj.name_ar)
                       .order_by('activity_name')[:100] if obj.name_ar else VendorActivity.objects.none())
    operations = obj.operations.all()[:200]

    # Products from ActivityProduct joined via activity_name
    va_names = list(activities.values_list('activity_name', flat=True).distinct())
    if not va_names and obj.name_ar:
        va_names = list(VendorActivity.objects.filter(
            supplier=None, vendor_name_raw=obj.name_ar
        ).values_list('activity_name', flat=True).distinct())
    from collections import defaultdict
    activity_products = defaultdict(list)
    for ap in ActivityProduct.objects.filter(activity_name__in=va_names).order_by('activity_name', 'product_code'):
        activity_products[ap.activity_name].append(ap)

    return render(request, 'vendors/detail.html', {
        'vendor': obj,
        'quals': quals,
        'invitations': invites,
        'activities': activities,
        'name_activities': name_activities,
        'activity_products': dict(activity_products),
        'operations': operations,
        'qual_form': QualificationForm(),
        'can_edit': request.user.is_superuser or _can(request.user, 'change'),
        'main_tasks': TaskMain.objects.all(),
    })


@module_required('suppliers', 'view')
def catalog(request):
    """v2026 activities catalogue — الأنشطة with products/services per activity."""
    qs = ActivityProduct.objects.all()
    main = request.GET.get('main') or ''
    activity = request.GET.get('activity') or ''
    q = (request.GET.get('q') or '').strip()
    mains = ActivityProduct.objects.values('main_code', 'main_name').distinct().order_by('main_code')
    acts = ActivityProduct.objects.values('activity_code', 'activity_name').distinct().order_by(
        'activity_code')
    if main:
        acts = acts.filter(main_code=main)
        qs = qs.filter(main_code=main)
    if activity:
        qs = qs.filter(activity_code=activity)
    if q:
        from django.db.models import Q as _Q
        qs = qs.filter(_Q(product_service__icontains=q) | _Q(activity_name__icontains=q) |
                       _Q(product_code__icontains=q))
    page = Paginator(qs.order_by('activity_code', 'product_code'), 60).get_page(request.GET.get('page'))
    return render(request, 'vendors/catalog.html', {
        'page': page, 'total': qs.count(), 'mains': mains, 'acts': acts,
        'selected_main': main, 'selected_activity': activity, 'filters': request.GET,
    })


def _can(user, action):
    from rbac import services
    return user.is_superuser or services.can(user, 'suppliers', action)


@module_required('suppliers', 'add')
def vendor_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Supplier {obj.supplier_no} created.')
            return redirect('vendor_detail', pk=obj.pk)
    else:
        form = SupplierForm(initial={'registration_status': 'local'})
    return render(request, 'vendors/form.html', {'form': form})


@module_required('suppliers', 'change')
def vendor_update(request, pk):
    obj = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Supplier {obj.supplier_no} updated.')
            return redirect('vendor_detail', pk=obj.pk)
    else:
        form = SupplierForm(instance=obj)
    return render(request, 'vendors/form.html', {'form': form, 'object': obj})


@module_required('suppliers', 'change')
def qualification_add(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = QualificationForm(request.POST)
        if form.is_valid():
            qual, created = SupplierQualification.objects.get_or_create(
                supplier=supplier, task_sub=form.cleaned_data['task_sub'],
                defaults={k: form.cleaned_data[k] for k in (
                    'registration_type', 'registration_capacity', 'brand',
                    'original_maker', 'origin_country', 'notes')})
            if not created:
                for k in ('registration_type', 'registration_capacity', 'brand',
                          'original_maker', 'origin_country', 'notes'):
                    setattr(qual, k, form.cleaned_data[k])
                qual.save()
            messages.success(request, f'Activity {qual.task_sub.code} saved for {supplier.supplier_no}.')
    return redirect('vendor_detail', pk=pk)


@module_required('suppliers', 'change')
def qualification_delete(request, pk, qpk):
    qual = get_object_or_404(SupplierQualification, supplier_id=pk, pk=qpk)
    if request.method == 'POST':
        record('DELETE', module='suppliers', model_label='vendors.SupplierQualification',
               object_id=qpk, object_repr=str(qual), changes=None)
        qual.delete()
        messages.success(request, 'Activity removed from supplier.')
    return redirect('vendor_detail', pk=pk)


@module_required('suppliers', 'view')
def tasks_browse(request):
    """v2026 'Tasks searsh' — find qualified vendors by activity."""
    main = request.GET.get('main') or ''
    sub = request.GET.get('sub') or ''
    subs = TaskSub.objects.select_related('main')
    suppliers = None
    if sub:
        suppliers = (SupplierQualification.objects.filter(task_sub_id=sub)
                     .select_related('supplier', 'task_sub', 'task_sub__main'))
    elif main:
        suppliers = (SupplierQualification.objects.filter(task_sub__main_id=main)
                     .select_related('supplier', 'task_sub', 'task_sub__main'))
    return render(request, 'vendors/tasks.html', {
        'mains': TaskMain.objects.all(),
        'subs': subs[:1000],
        'selected_main': main,
        'selected_sub': sub,
        'results': suppliers,
    })
