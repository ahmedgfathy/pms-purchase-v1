from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import permission_denied

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard'), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('purchases/', include('purchases.urls')),
    path('rfq/', include('rfq.urls')),
    path('vendors/', include('vendors.urls')),
    path('tenders/', include('tenders.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

handler403 = 'accounts.views.permission_denied'
