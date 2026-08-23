from django.urls import path

from . import views

urlpatterns = [
    path('', views.PurchaseRequestListView.as_view(), name='purchase_request_list'),
    path('new/', views.request_create, name='purchase_request_create'),
    path('<int:pk>/', views.PurchaseRequestDetailView.as_view(), name='purchase_request_detail'),
    path('<int:pk>/edit/', views.request_update, name='purchase_request_update'),
    path('<int:pk>/delete/', views.request_delete, name='purchase_request_delete'),
    path('<int:pk>/status/<str:status>/', views.request_set_status, name='purchase_request_status'),
]
