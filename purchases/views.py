from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from audit.models import record
from rbac import services
from rbac.decorators import module_required

from .forms import PurchaseRequestForm
from .models import PurchaseRequest


class ModuleRequiredMixin:
    module_code = 'purchases'
    action = 'view'

    def dispatch(self, request, *args, **kwargs):
        if not services.can(request.user, self.module_code, self.action):
            raise PermissionDenied(f"Missing '{self.action}' permission on module '{self.module_code}'")
        return super().dispatch(request, *args, **kwargs)


class PurchaseRequestListView(ModuleRequiredMixin, ListView):
    model = PurchaseRequest
    template_name = 'purchases/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20


class PurchaseRequestDetailView(ModuleRequiredMixin, DetailView):
    model = PurchaseRequest
    template_name = 'purchases/request_detail.html'
    context_object_name = 'request_obj'


@module_required('purchases', 'add')
def request_create(request):
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.requested_by = request.user
            if not request.user.is_superuser:
                employee = getattr(request.user, 'employee', None)
                if employee is not None:
                    obj.department_id = employee.department_id
            obj.save()
            messages.success(request, 'Purchase request created.')
            return redirect('purchase_request_detail', pk=obj.pk)
    else:
        form = PurchaseRequestForm(user=request.user)
    return render(request, 'purchases/request_form.html', {'form': form})


@module_required('purchases', 'change')
def request_update(request, pk):
    obj = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Purchase request updated.')
            return redirect('purchase_request_detail', pk=obj.pk)
    else:
        form = PurchaseRequestForm(instance=obj, user=request.user)
    return render(request, 'purchases/request_form.html', {'form': form, 'object': obj})


@module_required('purchases', 'change')
def request_set_status(request, pk, status):
    obj = get_object_or_404(PurchaseRequest, pk=pk)
    if status in dict(PurchaseRequest.STATUS_CHOICES) and request.method == 'POST':
        old_status = obj.status
        obj.status = status
        obj.save()
        record('UPDATE', module='purchases', model_label='purchases.PurchaseRequest',
               object_id=obj.pk, object_repr=str(obj),
               changes={'status': {'old': old_status, 'new': status}})
        messages.success(request, f'Status set to {status}.')
    return redirect('purchase_request_detail', pk=obj.pk)


@module_required('purchases', 'delete')
def request_delete(request, pk):
    obj = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Purchase request deleted.')
        return redirect('purchase_request_list')
    return render(request, 'purchases/request_confirm_delete.html', {'object': obj})
