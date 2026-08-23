from django.urls import path

from . import views

urlpatterns = [
    path('', views.tender_detail, name='tender_detail'),
    path('pos/', views.po_list, name='po_list'),
    path('pos/new/', views.po_create, name='po_create'),
    path('pos/<int:pk>/', views.po_detail, name='po_detail'),
    path('pos/<int:pk>/edit/', views.po_update, name='po_update'),
    path('pos/<int:pk>/delete/', views.po_delete, name='po_delete'),
    path('pos/<int:pk>/print/', views.po_print, name='po_print'),
    path('rfq/<int:rfq_pk>/', views.evaluation_board, name='evaluation_board'),
    path('rfq/<int:rfq_pk>/milestones/', views.save_milestones, name='save_milestones'),
    path('rfq/<int:rfq_pk>/rank/', views.rank_offers, name='rank_offers'),
    path('rfq/<int:rfq_pk>/eval/<int:inv_pk>/', views.invitation_evaluate, name='invitation_evaluate'),
    path('rfq/<int:rfq_pk>/award/<int:inv_pk>/', views.award, name='award'),
]
