from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('', views.dashboard, name='dashboard'),
    path('i18n/set/<str:lang>/', views.set_lang, name='set_lang'),
]
