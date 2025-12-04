from django.urls import path
from .views import (
    ClientDashboardView,
    CommercialDashboardView,
    AdminDashboardView,
    StartReservationView,
    ReservationSuccessView,
    PayReservationView,
    start_reservation_or_auth,
)

urlpatterns = [
    path('client/dashboard/', ClientDashboardView.as_view(), name='client_dashboard'),
    path('commercial/dashboard/', CommercialDashboardView.as_view(), name='commercial_dashboard'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('reserver/<uuid:unite_id>/', start_reservation_or_auth, name='reserve_unite'),
    path('reservation/<uuid:unite_id>/demarrer/', StartReservationView.as_view(), name='start_reservation'),
    path('reservation/<uuid:reservation_id>/confirmation/', ReservationSuccessView.as_view(), name='reservation_success'),
    path('reservation/<uuid:reservation_id>/payer/', PayReservationView.as_view(), name='pay_reservation'),
]
