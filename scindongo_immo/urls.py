from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from sales.views import DashboardAdminView
from catalog.views import HomeView, PourquoiInvestirView, ContactView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Pages publiques
    path('', HomeView.as_view(), name='home'),
    path('pourquoi-investir/', PourquoiInvestirView.as_view(), name='pourquoi_investir'),
    path('contact/', ContactView.as_view(), name='contact'),

    # Domaines applicatifs
    path('catalogue/', include('catalog.urls')),
    path('comptes/', include('accounts.urls')),
    path('ventes/', include('sales.urls')),
    path('api/', include('api.urls')),
    path("dashboards/admin/", DashboardAdminView.as_view(), name="admin-dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
