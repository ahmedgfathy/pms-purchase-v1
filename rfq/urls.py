from django.urls import path

from . import views

urlpatterns = [
    path('', views.rfq_list, name='rfq_list'),
    path('new/', views.rfq_create, name='rfq_create'),
    path('<int:pk>/', views.rfq_detail, name='rfq_detail'),
    path('<int:pk>/edit/', views.rfq_update, name='rfq_update'),
    path('<int:pk>/delete/', views.rfq_delete, name='rfq_delete'),
    path('<int:pk>/status/<str:status>/', views.rfq_set_status, name='rfq_status'),
    path('<int:pk>/vendors/pick/', views.vendor_pick, name='rfq_vendor_pick'),
    path('<int:pk>/vendorlist/', views.vendor_list_manage, name='rfq_vendor_list'),
    path('<int:pk>/vendorlist/print/', views.vendor_list_print, name='rfq_vendorlist_print'),
    path('<int:pk>/vendorlist/<int:inv_pk>/update/', views.invitation_update, name='invitation_update'),
    path('<int:pk>/vendorlist/<int:inv_pk>/delete/', views.invitation_delete, name='invitation_delete'),
]
