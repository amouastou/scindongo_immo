from django.urls import path
from .views import (
    ClientDashboardView,
    CommercialDashboardView,
    AdminDashboardView,
    StartReservationView,
    ReservationSuccessView,
    PayReservationView,
    start_reservation_or_auth,
    # Commercial views
    CommercialClientListView,
    CommercialClientCreateView,
    CommercialClientUpdateView,
    CommercialReservationListView,
    CommercialReservationDetailView,
    CommercialFinancementCreateView,
    CommercialFinancementUpdateView,
    CommercialContratCreateView,
    CommercialContratUpdateView,
    CommercialPaiementCreateView,
)

urlpatterns = [
    path('client/dashboard/', ClientDashboardView.as_view(), name='client_dashboard'),
    path('commercial/dashboard/', CommercialDashboardView.as_view(), name='commercial_dashboard'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('reserver/<uuid:unite_id>/', start_reservation_or_auth, name='reserve_unite'),
    path('reservation/<uuid:unite_id>/demarrer/', StartReservationView.as_view(), name='start_reservation'),
    path('reservation/<uuid:reservation_id>/confirmation/', ReservationSuccessView.as_view(), name='reservation_success'),
    path('reservation/<uuid:reservation_id>/payer/', PayReservationView.as_view(), name='pay_reservation'),
    
    # Commercial actions - Clients
    path('commercial/clients/', CommercialClientListView.as_view(), name='commercial_client_list'),
    path('commercial/clients/creer/', CommercialClientCreateView.as_view(), name='commercial_client_create'),
    path('commercial/clients/<uuid:pk>/modifier/', CommercialClientUpdateView.as_view(), name='commercial_client_update'),
    
    # Commercial actions - Réservations
    path('commercial/reservations/', CommercialReservationListView.as_view(), name='commercial_reservation_list'),
    path('commercial/reservations/<uuid:reservation_id>/', CommercialReservationDetailView.as_view(), name='commercial_reservation_detail'),
    
    # Commercial actions - Financements
    path('commercial/reservations/<uuid:reservation_id>/financement/creer/', CommercialFinancementCreateView.as_view(), name='commercial_financement_create'),
    path('commercial/reservations/<uuid:reservation_id>/financement/modifier/', CommercialFinancementUpdateView.as_view(), name='commercial_financement_update'),
    
    # Commercial actions - Contrats
    path('commercial/reservations/<uuid:reservation_id>/contrat/creer/', CommercialContratCreateView.as_view(), name='commercial_contrat_create'),
    path('commercial/reservations/<uuid:reservation_id>/contrat/modifier/', CommercialContratUpdateView.as_view(), name='commercial_contrat_update'),
    
    # Commercial actions - Paiements
    path('commercial/reservations/<uuid:reservation_id>/paiement/creer/', CommercialPaiementCreateView.as_view(), name='commercial_paiement_create'),
]
