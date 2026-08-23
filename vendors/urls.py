from django.urls import path

from . import views

urlpatterns = [
    path('', views.vendor_list, name='vendor_list'),
    path('tasks/', views.tasks_browse, name='vendor_tasks'),
    path('catalog/', views.catalog, name='vendor_catalog'),
    path('new/', views.vendor_create, name='vendor_create'),
    path('<int:pk>/', views.vendor_detail, name='vendor_detail'),
    path('<int:pk>/edit/', views.vendor_update, name='vendor_update'),
    path('<int:pk>/qual/add/', views.qualification_add, name='qualification_add'),
    path('<int:pk>/qual/<int:qpk>/delete/', views.qualification_delete, name='qualification_delete'),
]
