from django.urls import path
from .views import (
    ClientDashboardView,
    CommercialDashboardView,
    AdminDashboardView,
    ReservationDocumentsUploadView,
    ReservationDocumentModifyView,
    CommercialDocumentRejectView,
    CommercialDocumentValidateView,
    FinancementDocumentsUploadView,
    FinancementDocumentModifyView,
    CommercialFinancingDocumentRejectView,
    CommercialFinancingDocumentValidateView,
    StartReservationView,
    ReservationSuccessView,
    ClientReservationDetailView,
    PayReservationView,
    ClientPaymentModeChoiceView,
    ClientDirectPaymentView,
    ClientFinancingRequestView,
    ClientFinancingDetailView,
    CommercialPaymentValidationListView,
    CommercialPaymentValidateView,
    start_reservation_or_auth,
    # Commercial views
    CommercialReservationConfirmView,
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
    # Banque Partenaire views
    BanquePartenaireCreateView,
    BanquePartenaireUpdateView,
    BanquePartenaireListView,
    # Financing Management views
    CommercialFinancingListView,
    CommercialFinancingDetailView,
    # OTP Contract Signature views
    CommercialGenerateOTPView,
    ClientSignContratView,
)

urlpatterns = [
    path('client/dashboard/', ClientDashboardView.as_view(), name='client_dashboard'),
    path('commercial/dashboard/', CommercialDashboardView.as_view(), name='commercial_dashboard'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Documents réservation
    path('reservation/<uuid:reservation_id>/documents/', ReservationDocumentsUploadView.as_view(), name='reservation_documents_upload'),
    path('reservation/document/<uuid:document_id>/modify/', ReservationDocumentModifyView.as_view(), name='reservation_document_modify'),
    path('commercial/document/<uuid:document_id>/reject/', CommercialDocumentRejectView.as_view(), name='commercial_document_reject'),
    path('commercial/document/<uuid:document_id>/validate/', CommercialDocumentValidateView.as_view(), name='commercial_document_validate'),
    
    # Documents financement
    path('financement/<uuid:financement_id>/documents/', FinancementDocumentsUploadView.as_view(), name='financing_documents_upload'),
    path('financement/document/<uuid:document_id>/modify/', FinancementDocumentModifyView.as_view(), name='financing_document_modify'),
    path('commercial/financement/document/<uuid:document_id>/reject/', CommercialFinancingDocumentRejectView.as_view(), name='commercial_financing_document_reject'),
    path('commercial/financement/document/<uuid:document_id>/validate/', CommercialFinancingDocumentValidateView.as_view(), name='commercial_financing_document_validate'),
    
    path('reserver/<uuid:unite_id>/', start_reservation_or_auth, name='reserve_unite'),
    path('reservation/<uuid:unite_id>/demarrer/', StartReservationView.as_view(), name='start_reservation'),
    path('reservation/<uuid:reservation_id>/confirmation/', ReservationSuccessView.as_view(), name='reservation_success'),
    path('reservation/<uuid:reservation_id>/detail/', ClientReservationDetailView.as_view(), name='client_reservation_detail'),
    path('reservation/<uuid:reservation_id>/payer/', PayReservationView.as_view(), name='pay_reservation'),
    path('reservation/<uuid:reservation_id>/choix-paiement/', ClientPaymentModeChoiceView.as_view(), name='client_payment_mode_choice'),
    path('reservation/<uuid:reservation_id>/paiement-direct/', ClientDirectPaymentView.as_view(), name='client_direct_payment'),
    path('reservation/<uuid:reservation_id>/financement-bancaire/', ClientFinancingRequestView.as_view(), name='client_financing_request'),
    path('financement/<uuid:financement_id>/detail/', ClientFinancingDetailView.as_view(), name='client_financing_detail'),
    
    # Commercial actions - Clients
    path('commercial/clients/', CommercialClientListView.as_view(), name='commercial_client_list'),
    path('commercial/clients/creer/', CommercialClientCreateView.as_view(), name='commercial_client_create'),
    path('commercial/clients/<uuid:pk>/modifier/', CommercialClientUpdateView.as_view(), name='commercial_client_update'),
    
    # Commercial actions - Réservations
    path('commercial/reservations/', CommercialReservationListView.as_view(), name='commercial_reservation_list'),
    path('commercial/reservations/<uuid:reservation_id>/', CommercialReservationDetailView.as_view(), name='commercial_reservation_detail'),
    path('commercial/reservations/<uuid:reservation_id>/confirmer/', CommercialReservationConfirmView.as_view(), name='commercial_reservation_confirm'),
    
    # Commercial actions - Financements
    path('commercial/reservations/<uuid:reservation_id>/financement/creer/', CommercialFinancementCreateView.as_view(), name='commercial_financement_create'),
    path('commercial/reservations/<uuid:reservation_id>/financement/modifier/', CommercialFinancementUpdateView.as_view(), name='commercial_financement_update'),
    
    # Commercial actions - Contrats
    path('commercial/reservations/<uuid:reservation_id>/contrat/creer/', CommercialContratCreateView.as_view(), name='commercial_contrat_create'),
    path('commercial/reservations/<uuid:reservation_id>/contrat/modifier/', CommercialContratUpdateView.as_view(), name='commercial_contrat_update'),
    
    # Commercial actions - Paiements
    path('commercial/reservations/<uuid:reservation_id>/paiement/creer/', CommercialPaiementCreateView.as_view(), name='commercial_paiement_create'),
    path('commercial/paiements/validation/', CommercialPaymentValidationListView.as_view(), name='commercial_payment_validation_list'),
    path('commercial/paiements/<uuid:paiement_id>/valider/', CommercialPaymentValidateView.as_view(), name='commercial_payment_validate'),
    
    # OTP Contract Signature
    path('contrats/<uuid:contrat_id>/generate-otp/', CommercialGenerateOTPView.as_view(), name='commercial_generate_otp'),
    path('reservations/<uuid:reservation_id>/contrats/<uuid:contrat_id>/sign/', ClientSignContratView.as_view(), name='client_sign_contrat'),
    
    # Banques partenaires
    path('banques/', BanquePartenaireListView.as_view(), name='banque_partenaire_list'),
    path('banques/add/', BanquePartenaireCreateView.as_view(), name='banque_partenaire_add'),
    path('banques/<uuid:pk>/edit/', BanquePartenaireUpdateView.as_view(), name='banque_partenaire_edit'),
    
    # Gestion des demandes de financement
    path('commercial/financements/', CommercialFinancingListView.as_view(), name='commercial_financing_list'),
    path('commercial/financements/<uuid:financement_id>/', CommercialFinancingDetailView.as_view(), name='commercial_financing_detail'),
]
