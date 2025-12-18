from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.formats import number_format
from django.contrib import messages
from django.http import Http404, HttpResponse, FileResponse
from django.core.exceptions import PermissionDenied
from django.conf import settings
import csv
import logging
from datetime import datetime

from accounts.mixins import RoleRequiredMixin
from accounts.models import User, Role
from accounts.utils import is_admin_user
from catalog.models import Unite, MessageChantier, AvancementChantierUnite, Programme
from .models import Client, Reservation, ReservationDocument, FinancementDocument, Paiement, Contrat, Financement, BanquePartenaire, EcheanceLoyer
from .forms import (
    ReservationForm,
    ReservationDocumentForm,
    FinancementDocumentForm,
    PaiementForm,
    ClientForm,
    FinancementForm,
    ContratForm,
    PaymentModeForm,
    FinancingRequestForm,
    EcheancePaiementForm,
)
from .utils import set_pending_unite, calculer_montant_caution, get_next_echeances_a_payer
from .document_services import ReservationDocumentService
from .financing_document_service import FinancementDocumentService
from .mixins import ReservationRequiredMixin, FinancementFormMixin, ContratFormMixin, PaiementFormMixin
from .services.signature_service import SignatureService
from .services.payment_receipt_service import generate_payment_receipt
from .services.contract_pdf_service import generate_contract_pdf
from core.utils import audit_log
from core.choices import PaiementStatus, PaiementType, UniteStatus, OperationType, ContratStatus, FinancementStatus
from django.db.models import Sum, Count, Q
from dateutil.relativedelta import relativedelta


logger = logging.getLogger(__name__)


def restrict_queryset(qs, user, relation_path):
    if is_admin_user(user):
        return qs
    return qs.filter(**{relation_path: user})


def ensure_programme_access(programme, user):
    if is_admin_user(user):
        return
    if not programme or programme.contact_commercial != user:
        raise PermissionDenied("Accès non autorisé à ce programme.")


class CommercialReservationAccessMixin:
    reservation_url_kwarg = 'reservation_id'

    def get_reservation_queryset(self):
        return Reservation.objects.select_related('client', 'unite', 'unite__programme').prefetch_related('documents', 'paiements')

    def get_reservation(self):
        reservation_id = self.kwargs.get(self.reservation_url_kwarg)
        qs = restrict_queryset(self.get_reservation_queryset(), self.request.user, 'unite__programme__contact_commercial')
        return get_object_or_404(qs, id=reservation_id)


# ============================
#   RESERVATION DOCUMENTS
# ============================


class ReservationDocumentsUploadView(RoleRequiredMixin, TemplateView):
    """Vue pour uploader documents lors de réservation"""
    template_name = 'sales/reservation_documents_upload.html'
    required_roles = ["CLIENT"]

    def get_reservation(self):
        """Récupérer la réservation du client"""
        reservation = get_object_or_404(
            Reservation,
            id=self.kwargs['reservation_id'],
            client=self.request.user.client_profile
        )
        return reservation

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        
        ctx['reservation'] = reservation
        ctx['documents'] = reservation.documents.all()
        ctx['form'] = ReservationDocumentForm()
        
        # Vérifier si tous docs requis sont validés
        can_reserve, _ = ReservationDocumentService.can_make_reservation(reservation)
        ctx['can_reserve'] = can_reserve
        ctx['missing_documents'] = ReservationDocumentService.get_missing_documents(reservation)
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Uploader un nouveau document"""
        reservation = self.get_reservation()
        form = ReservationDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Vérifier qu'on n'a pas déjà ce type de doc
            existing = ReservationDocument.objects.filter(
                reservation=reservation,
                document_type=form.cleaned_data['document_type']
            ).first()
            
            if existing:
                existing.fichier.delete()  # Supprimer ancien fichier
                existing.fichier = form.cleaned_data['fichier']
                existing.statut = 'en_attente'  # Réinitialiser statut
                existing.raison_rejet = ''
                existing.verifie_par = None
                existing.verifie_le = None
                existing.save()
                messages.success(request, f"Document '{existing.get_document_type_display()}' mis à jour")
            else:
                doc = form.save(commit=False)
                doc.reservation = reservation
                doc.save()
                messages.success(request, f"Document '{doc.get_document_type_display()}' uploadé avec succès")
            
            # Log audit
            audit_log(request.user, reservation, 'reservation_document_uploaded',
                     {'document_type': form.cleaned_data['document_type']}, request)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        return redirect('reservation_documents_upload', reservation_id=reservation.id)


class ReservationDocumentModifyView(RoleRequiredMixin, TemplateView):
    """Vue pour modifier UN document spécifique - évite problème modal clignotant"""
    template_name = 'sales/reservation_document_modify.html'
    required_roles = ["CLIENT"]

    def get_document(self):
        """Récupérer le document et vérifier que c'est du client"""
        doc = get_object_or_404(ReservationDocument, id=self.kwargs['document_id'])
        client = get_object_or_404(Client, user=self.request.user)
        
        # Vérifier que le document appartient à une réservation du client
        if doc.reservation.client != client:
            raise Http404("Document non trouvé")
        
        return doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = self.get_document()
        
        ctx['document'] = doc
        ctx['reservation'] = doc.reservation
        ctx['form'] = ReservationDocumentForm()
        ctx['document_type_label'] = doc.get_document_type_display()
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Modifier le document"""
        doc = self.get_document()
        form = ReservationDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Supprimer ancien fichier
            if doc.fichier:
                doc.fichier.delete()
            
            # Sauvegarder nouveau fichier
            doc.fichier = form.cleaned_data['fichier']
            doc.statut = 'en_attente'  # Réinitialiser statut
            doc.raison_rejet = ''
            doc.verifie_par = None
            doc.verifie_le = None
            doc.save()
            
            messages.success(request, f"✅ Document '{doc.get_document_type_display()}' mis à jour avec succès!")
            
            # Log audit
            audit_log(request.user, doc, 'reservation_document_updated',
                     {'document_type': doc.document_type}, request)
            
            # Rediriger vers détail réservation
            return redirect('client_reservation_detail', reservation_id=doc.reservation.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        return render(request, self.template_name, self.get_context_data())


class CommercialDocumentRejectView(RoleRequiredMixin, TemplateView):
    """Vue pour que le Commercial rejette un document - évite problème modal clignotant"""
    template_name = 'sales/commercial_document_reject.html'
    required_roles = ["COMMERCIAL"]

    def get_document_queryset(self):
        return ReservationDocument.objects.select_related('reservation', 'reservation__unite', 'reservation__unite__programme')

    def get_document(self):
        """Récupérer le document accessible au commercial"""
        qs = restrict_queryset(self.get_document_queryset(), self.request.user, 'reservation__unite__programme__contact_commercial')
        doc = get_object_or_404(qs, id=self.kwargs['document_id'])
        return doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = self.get_document()
        
        ctx['document'] = doc
        ctx['reservation'] = doc.reservation
        ctx['document_type_label'] = doc.get_document_type_display()
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Rejeter le document"""
        doc = self.get_document()
        raison = request.POST.get('raison_rejet', '').strip()
        
        if not raison:
            messages.error(request, "Veuillez fournir une raison de rejet")
            return render(request, self.template_name, self.get_context_data())
        
        # Mettre à jour le document
        doc.statut = 'rejete'
        doc.raison_rejet = raison
        doc.verifie_par = request.user
        doc.verifie_le = timezone.now()
        doc.save()
        
        messages.warning(request, f"❌ Document '{doc.get_document_type_display()}' rejeté - client averti")
        
        # Log audit
        audit_log(request.user, doc, 'document_rejected', 
                 {'reason': raison[:100]}, request)
        
        # Rediriger vers détail réservation du commercial
        return redirect('commercial_reservation_detail', reservation_id=doc.reservation.id)


class CommercialDocumentValidateView(RoleRequiredMixin, TemplateView):
    """Vue pour que le Commercial valide un document (direct, pas de modal)"""
    template_name = 'sales/commercial_document_validate.html'
    required_roles = ["COMMERCIAL"]

    def get_document_queryset(self):
        return ReservationDocument.objects.select_related('reservation', 'reservation__unite', 'reservation__unite__programme')

    def get_document(self):
        """Récupérer le document"""
        qs = restrict_queryset(self.get_document_queryset(), self.request.user, 'reservation__unite__programme__contact_commercial')
        doc = get_object_or_404(qs, id=self.kwargs['document_id'])
        return doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = self.get_document()
        
        ctx['document'] = doc
        ctx['reservation'] = doc.reservation
        ctx['document_type_label'] = doc.get_document_type_display()
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Valider le document"""
        doc = self.get_document()
        reservation_id = doc.reservation.id
        
        # Valider
        doc.statut = 'valide'
        doc.verifie_par = request.user
        doc.verifie_le = timezone.now()
        doc.save()
        
        messages.success(request, f"✅ Document '{doc.get_document_type_display()}' validé")
        
        # Log audit
        audit_log(request.user, doc, 'document_validated', 
                 {'document_type': doc.document_type}, request)
        
        # Rediriger vers détail réservation du commercial
        return redirect('commercial_reservation_detail', reservation_id=reservation_id)


# ============================
#   FINANCEMENT DOCUMENTS VIEWS
# ============================


class FinancementDocumentsUploadView(RoleRequiredMixin, TemplateView):
    """Vue pour uploader documents de financement"""
    template_name = 'sales/financing_documents_upload.html'
    required_roles = ["CLIENT"]

    def get_financement(self):
        """Récupérer le financement du client"""
        try:
            client = Client.objects.get(user=self.request.user)
        except Client.DoesNotExist:
            raise Http404("Profil client non trouvé")
        
        financement = get_object_or_404(
            Financement,
            id=self.kwargs['financement_id'],
            reservation__client=client
        )
        return financement

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        financement = self.get_financement()
        
        ctx['financement'] = financement
        ctx['reservation'] = financement.reservation
        ctx['documents'] = financement.documents.all()
        
        # Ajouter formulaire vierge pour GET
        if 'form' not in ctx:
            ctx['form'] = FinancementDocumentForm()

        # Vérifier si tous docs requis sont validés
        service = FinancementDocumentService()
        can_proceed, _ = service.can_proceed_financing(financement)
        ctx['can_proceed'] = can_proceed
        ctx['docs_complete'] = can_proceed
        ctx['missing_documents'] = service.get_missing_documents(financement)
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Uploader un nouveau document"""
        financement = self.get_financement()
        form = FinancementDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            doc_type = form.cleaned_data['document_type']
            
            # Types de documents qui peuvent être multiples
            multiple_types = ['bulletin_salaire']  # Peut avoir 3 bulletins de salaire
            
            if doc_type in multiple_types:
                # Pour les bulletins de salaire: ajouter un nouveau document
                # Calculer le prochain numéro d'ordre
                existing_count = FinancementDocument.objects.filter(
                    financement=financement,
                    document_type=doc_type
                ).count()
                
                next_numero = existing_count + 1
                
                # Limiter à 3 bulletins
                if next_numero > 3:
                    messages.error(request, "Vous pouvez uploader maximum 3 bulletins de salaire")
                else:
                    doc = form.save(commit=False)
                    doc.financement = financement
                    doc.numero_ordre = next_numero
                    doc.save()
                    messages.success(request, f"Document '{doc.get_document_label()}' uploadé avec succès")
                    
                    # Log audit
                    audit_log(request.user, financement, 'financing_document_uploaded',
                             {'document_type': doc_type, 'numero_ordre': next_numero}, request)
            else:
                # Pour les autres documents: remplacer s'il existe
                existing = FinancementDocument.objects.filter(
                    financement=financement,
                    document_type=doc_type,
                    numero_ordre=1
                ).first()
                
                if existing:
                    existing.fichier.delete()  # Supprimer ancien fichier
                    existing.fichier = form.cleaned_data['fichier']
                    existing.statut = 'en_attente'  # Réinitialiser statut
                    existing.raison_rejet = ''
                    existing.verifie_par = None
                    existing.verifie_le = None
                    existing.save()
                    messages.success(request, f"Document '{existing.get_document_type_display()}' mis à jour")
                else:
                    doc = form.save(commit=False)
                    doc.financement = financement
                    doc.numero_ordre = 1
                    doc.save()
                    messages.success(request, f"Document '{doc.get_document_type_display()}' uploadé avec succès")
                
                # Log audit
                audit_log(request.user, financement, 'financing_document_uploaded',
                         {'document_type': doc_type}, request)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        return redirect('financing_documents_upload', financement_id=financement.id)


class FinancementDocumentModifyView(RoleRequiredMixin, TemplateView):
    """Vue pour modifier UN document de financement spécifique"""
    template_name = 'sales/financing_document_modify.html'
    required_roles = ["CLIENT"]

    def get_document(self):
        """Récupérer le document et vérifier que c'est du client"""
        doc = get_object_or_404(FinancementDocument, id=self.kwargs['document_id'])
        client = get_object_or_404(Client, user=self.request.user)
        
        # Vérifier que le document appartient à un financement du client
        if doc.financement.reservation.client != client:
            raise Http404("Document non trouvé")
        
        return doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = self.get_document()
        
        ctx['document'] = doc
        ctx['financement'] = doc.financement
        ctx['reservation'] = doc.financement.reservation
        from .forms import FinancementDocumentUpdateForm
        ctx['form'] = FinancementDocumentUpdateForm(instance=doc)
        ctx['document_type_label'] = doc.get_document_label()
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Modifier le document"""
        doc = self.get_document()
        from .forms import FinancementDocumentUpdateForm
        form = FinancementDocumentUpdateForm(request.POST, request.FILES, instance=doc)
        
        if form.is_valid():
            # Django va automatiquement remplacer l'ancien fichier
            # Il faut juste s'assurer que le nouveau fichier est bien présent
            if 'fichier' in request.FILES:
                # Sauvegarder le formulaire qui va uploader le nouveau fichier
                updated_doc = form.save(commit=False)
                updated_doc.statut = 'en_attente'  # Réinitialiser statut
                updated_doc.raison_rejet = ''
                updated_doc.verifie_par = None
                updated_doc.verifie_le = None
                updated_doc.save()
                
                messages.success(request, f"✅ Document '{updated_doc.get_document_label()}' mis à jour avec succès!")
                
                # Log audit
                audit_log(request.user, updated_doc, 'financing_document_updated',
                         {'document_type': updated_doc.document_type}, request)
                
                # Rediriger vers page financements du client
                return redirect('financing_documents_upload', financement_id=updated_doc.financement.id)
            else:
                messages.error(request, "Veuillez sélectionner un fichier à uploader")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        return render(request, self.template_name, self.get_context_data())


class CommercialFinancingDocumentRejectView(RoleRequiredMixin, TemplateView):
    """Vue pour que le Commercial rejette un document de financement"""
    template_name = 'sales/commercial_financing_document_reject.html'
    required_roles = ["COMMERCIAL"]

    def get_document_queryset(self):
        return FinancementDocument.objects.select_related(
            'financement', 'financement__reservation', 'financement__reservation__unite', 'financement__reservation__unite__programme'
        )

    def get_document(self):
        """Récupérer le document"""
        qs = restrict_queryset(
            self.get_document_queryset(),
            self.request.user,
            'financement__reservation__unite__programme__contact_commercial'
        )
        doc = get_object_or_404(qs, id=self.kwargs['document_id'])
        return doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = self.get_document()
        
        ctx['document'] = doc
        ctx['financement'] = doc.financement
        ctx['reservation'] = doc.financement.reservation
        ctx['document_type_label'] = doc.get_document_label()
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Rejeter le document"""
        doc = self.get_document()
        raison = request.POST.get('raison_rejet', '').strip()
        
        if not raison:
            messages.error(request, "Veuillez fournir une raison de rejet")
            return render(request, self.template_name, self.get_context_data())
        
        # Mettre à jour le document
        doc.statut = 'rejete'
        doc.raison_rejet = raison
        doc.verifie_par = request.user
        doc.verifie_le = timezone.now()
        doc.save()
        
        messages.warning(request, f"❌ Document '{doc.get_document_label()}' rejeté - client averti")
        
        # Log audit
        audit_log(request.user, doc, 'financing_document_rejected', 
                 {'reason': raison[:100]}, request)
        
        # Rediriger vers détail financement du commercial
        return redirect('commercial_financing_detail', financement_id=doc.financement.id)


class CommercialFinancingDocumentValidateView(RoleRequiredMixin, TemplateView):
    """Vue pour que le Commercial valide un document de financement"""
    template_name = 'sales/commercial_financing_document_validate.html'
    required_roles = ["COMMERCIAL"]

    def get_document_queryset(self):
        return FinancementDocument.objects.select_related(
            'financement', 'financement__reservation', 'financement__reservation__unite', 'financement__reservation__unite__programme'
        )

    def get_document(self):
        """Récupérer le document"""
        qs = restrict_queryset(
            self.get_document_queryset(),
            self.request.user,
            'financement__reservation__unite__programme__contact_commercial'
        )
        doc = get_object_or_404(qs, id=self.kwargs['document_id'])
        return doc

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        doc = self.get_document()
        
        ctx['document'] = doc
        ctx['financement'] = doc.financement
        ctx['reservation'] = doc.financement.reservation
        ctx['document_type_label'] = doc.get_document_label()
        
        return ctx

    def post(self, request, *args, **kwargs):
        """Valider le document"""
        doc = self.get_document()
        financement_id = doc.financement.id
        
        # Valider
        doc.statut = 'valide'
        doc.verifie_par = request.user
        doc.verifie_le = timezone.now()
        doc.save()
        
        messages.success(request, f"✅ Document '{doc.get_document_label()}' validé")
        
        # Log audit
        audit_log(request.user, doc, 'financing_document_validated', 
                 {'document_type': doc.document_type}, request)
        
        # Rediriger vers détail financement du commercial
        return redirect('commercial_financing_detail', financement_id=financement_id)


class ClientDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboards/client_dashboard.html'
    required_roles = ["CLIENT"]

    def get_context_data(self, **kwargs):
        from .models import Contrat, Financement, EcheanceLoyer
        from core.choices import PaiementStatus
        
        ctx = super().get_context_data(**kwargs)
        client = getattr(self.request.user, "client_profile", None)
        if client:
            ctx["reservations"] = client.reservations.select_related("unite", "unite__programme").prefetch_related("paiements", "documents")
            ctx["paiements"] = Paiement.objects.filter(reservation__client=client).select_related("reservation")
            ctx["contrats"] = Contrat.objects.filter(reservation__client=client).select_related("reservation")
            ctx["financements"] = Financement.objects.filter(reservation__client=client).select_related("reservation", "banque").prefetch_related("echeances")
            
            # 🏘️ NOUVEAU : Échéances en attente de paiement (locations)
            ctx["echeances_en_attente"] = get_next_echeances_a_payer(client)[:20]

            # 🔐 Cautions obligatoires non encore payées
            reservations_location = client.reservations.filter(
                unite__programme__type_operation=OperationType.LOCATION
            )
            reservations_sans_caution = reservations_location.annotate(
                caution_count=Count(
                    'paiements',
                    filter=Q(
                        paiements__type_paiement=PaiementType.CAUTION,
                        paiements__statut__in=[PaiementStatus.ENREGISTRE, PaiementStatus.VALIDE],
                    ),
                )
            ).filter(caution_count=0)

            cautions_en_attente = []
            for reservation in reservations_sans_caution.select_related('unite', 'unite__programme'):
                try:
                    montant_caution = calculer_montant_caution(reservation)
                except Exception:
                    continue
                cautions_en_attente.append({
                    "reservation": reservation,
                    "montant": montant_caution,
                })
            ctx["cautions_en_attente"] = cautions_en_attente
        else:
            ctx["reservations"] = []
            ctx["paiements"] = []
            ctx["contrats"] = []
            ctx["financements"] = []
            ctx["echeances_en_attente"] = []
            ctx["cautions_en_attente"] = []
        return ctx


class CommercialDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboards/commercial_dashboard.html'
    required_roles = ["COMMERCIAL"]

    def get_context_data(self, **kwargs):
        from .models import Reservation, Paiement, Financement, Contrat
        from catalog.models import Programme, Unite
        from accounts.models import User, Role
        
        ctx = super().get_context_data(**kwargs)
        
        # 🔒 FILTRAGE: Commercial ne voit QUE ses programmes
        user = self.request.user
        is_admin = is_admin_user(user)
        
        # Comptes (filtrés par commercial)
        if is_admin:
            ctx["clients_count"] = Client.objects.count()
            ctx["reservations_count"] = Reservation.objects.count()
            ctx["paiements_count"] = Paiement.objects.count()
            ctx["financements_count"] = Financement.objects.count()
        else:
            # Seulement les clients ayant réservé sur MES programmes
            ctx["clients_count"] = Client.objects.filter(
                reservations__unite__programme__contact_commercial=user
            ).distinct().count()
            ctx["reservations_count"] = Reservation.objects.filter(
                unite__programme__contact_commercial=user
            ).count()
            ctx["paiements_count"] = Paiement.objects.filter(
                reservation__unite__programme__contact_commercial=user
            ).count()
            ctx["financements_count"] = Financement.objects.filter(
                reservation__unite__programme__contact_commercial=user
            ).count()
        
        # ÉTAPE 3: Réservations en attente (en_cours) en priorité
        pending_qs = Reservation.objects.filter(statut="en_cours")
        if not is_admin:
            pending_qs = pending_qs.filter(unite__programme__contact_commercial=user)
        ctx["pending_reservations"] = pending_qs.select_related(
            "client", "unite", "unite__programme"
        ).prefetch_related("paiements", "documents").order_by('-created_at')
        ctx["pending_count"] = ctx["pending_reservations"].count()
        
        # ÉTAPE 8: Distinguer paiements VENTE vs cautions LOCATION en attente
        pending_vente_qs = Paiement.objects.filter(
            statut=PaiementStatus.ENREGISTRE,
            type_paiement__in=[PaiementType.ACOMPTE, PaiementType.SOLDE]
        )
        pending_caution_qs = Paiement.objects.filter(
            statut=PaiementStatus.ENREGISTRE,
            type_paiement=PaiementType.CAUTION
        )
        if not is_admin:
            pending_vente_qs = pending_vente_qs.filter(reservation__unite__programme__contact_commercial=user)
            pending_caution_qs = pending_caution_qs.filter(reservation__unite__programme__contact_commercial=user)

        pending_vente_qs = pending_vente_qs.select_related(
            "reservation", "reservation__client", "reservation__unite"
        ).order_by('-created_at')
        pending_caution_qs = pending_caution_qs.select_related(
            "reservation", "reservation__client", "reservation__unite"
        ).order_by('-created_at')

        ctx["pending_vente_payments"] = pending_vente_qs
        ctx["pending_caution_payments"] = pending_caution_qs
        ctx["pending_vente_payments_count"] = pending_vente_qs.count()
        ctx["pending_caution_payments_count"] = pending_caution_qs.count()
        ctx["pending_payments_total_count"] = (
            ctx["pending_vente_payments_count"] + ctx["pending_caution_payments_count"]
        )

        preview_payments = list(pending_vente_qs[:10]) + list(pending_caution_qs[:10])
        preview_payments.sort(key=lambda p: p.created_at, reverse=True)
        ctx["pending_payments_preview"] = preview_payments
        
        # Listes détaillées (filtrées par commercial)
        reservations_qs = Reservation.objects.select_related("client", "unite", "unite__programme").prefetch_related("paiements", "documents")
        clients_qs = Client.objects.select_related("user")
        paiements_qs = Paiement.objects.select_related("reservation", "reservation__client")
        financements_qs = Financement.objects.select_related("banque", "reservation", "reservation__client").prefetch_related("echeances")
        programmes_qs = Programme.objects.filter(statut="actif").prefetch_related("unites")
        
        if not is_admin:
            reservations_qs = reservations_qs.filter(unite__programme__contact_commercial=user)
            clients_qs = clients_qs.filter(reservations__unite__programme__contact_commercial=user).distinct()
            paiements_qs = paiements_qs.filter(reservation__unite__programme__contact_commercial=user)
            financements_qs = financements_qs.filter(reservation__unite__programme__contact_commercial=user)
            programmes_qs = programmes_qs.filter(contact_commercial=user)
        
        ctx["reservations"] = reservations_qs[:20]
        ctx["clients"] = clients_qs[:20]
        ctx["paiements_vente"] = pending_vente_qs[:20]
        ctx["paiements_caution"] = pending_caution_qs[:20]
        ctx["financements"] = financements_qs[:20]
        ctx["programmes"] = programmes_qs.all()
        
        # Échéances de loyer: distinguer non payées vs paiements en attente
        from core.choices import UniteStatus, OperationType
        # Échéances qui ont un paiement enregistré mais en attente de validation (alimentent les validations)
        echeances_en_attente_qs = EcheanceLoyer.objects.filter(
            paiement__isnull=False,
            statut_paiement=PaiementStatus.ENREGISTRE,
            reservation__unite__programme__type_operation=OperationType.LOCATION
        ).select_related('reservation__client', 'reservation__unite__programme').order_by('date_echeance')
        # Échéances non payées (à payer par le client)
        echeances_non_payees_qs = EcheanceLoyer.objects.filter(
            paiement__isnull=True,
            reservation__unite__programme__type_operation=OperationType.LOCATION
        ).select_related('reservation__client', 'reservation__unite__programme').order_by('date_echeance')

        if not is_admin:
            echeances_en_attente_qs = echeances_en_attente_qs.filter(reservation__unite__programme__contact_commercial=user)
            echeances_non_payees_qs = echeances_non_payees_qs.filter(reservation__unite__programme__contact_commercial=user)

        # Exposer dans le contexte les deux jeux de résultats et un compteur utilisé dans le template
        ctx["echeances_en_attente"] = echeances_en_attente_qs[:20]
        ctx["echeances_non_payees"] = echeances_non_payees_qs[:20]
        ctx["pending_echeances_count"] = echeances_en_attente_qs.count()
        
        # Unités en chantier (réservées ou vendues) - VENTE UNIQUEMENT
        chantiers_qs = Unite.objects.filter(
            statut_disponibilite__in=[UniteStatus.RESERVE, UniteStatus.VENDU],
            programme__type_operation=OperationType.VENTE  # 🏠 Exclure locations
        ).select_related('programme').prefetch_related('avancements_chantier')
        if not is_admin:
            chantiers_qs = chantiers_qs.filter(programme__contact_commercial=user)
        ctx["chantiers_unites"] = chantiers_qs.order_by('-updated_at')[:20]
        
        return ctx


class CommercialSearchUniteView(RoleRequiredMixin, TemplateView):
    """
    Vue de recherche unifiée pour le commercial.
    Recherche par référence lot et affiche toutes les infos pertinentes.
    """
    template_name = 'sales/commercial_search_unite.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        is_admin = is_admin_user(user)
        
        # Récupérer le terme de recherche
        search_query = self.request.GET.get('q', '').strip()
        ctx['search_query'] = search_query
        
        if not search_query:
            ctx['show_results'] = False
            return ctx
        
        # Rechercher l'unité par référence lot
        unite_qs = Unite.objects.select_related(
            'programme', 'modele_bien', 'modele_bien__type_bien'
        ).prefetch_related('reservations')
        
        # Filtrage par commercial (sauf admin)
        if not is_admin:
            unite_qs = unite_qs.filter(programme__contact_commercial=user)
        
        # Recherche par référence exacte ou partielle
        unite = unite_qs.filter(
            Q(reference_lot__iexact=search_query) | 
            Q(reference_lot__icontains=search_query)
        ).first()
        
        if not unite:
            ctx['show_results'] = False
            ctx['error_message'] = f"Aucun bien trouvé avec la référence '{search_query}'"
            return ctx
        
        ctx['show_results'] = True
        ctx['unite'] = unite
        ctx['programme'] = unite.programme
        ctx['is_location'] = unite.programme.is_location()
        ctx['is_vente'] = unite.programme.is_vente()
        
        # Récupérer la réservation active (en_cours ou confirmee)
        reservation = unite.reservations.filter(
            statut__in=['en_cours', 'confirmee']
        ).select_related('client', 'client__user').prefetch_related(
            'paiements', 'documents', 'echeances_loyer'
        ).first()
        
        ctx['reservation'] = reservation
        
        if reservation:
            ctx['client'] = reservation.client
            
            # Paiements
            paiements = reservation.paiements.all().order_by('-date_paiement')
            ctx['paiements'] = paiements
            ctx['paiements_valides'] = paiements.filter(statut='valide')
            ctx['paiements_en_attente'] = paiements.filter(statut='enregistre')
            ctx['total_paye'] = sum(p.montant for p in paiements if p.statut == 'valide')
            
            # Contrat
            ctx['has_contrat'] = hasattr(reservation, 'contrat')
            if ctx['has_contrat']:
                ctx['contrat'] = reservation.contrat
            
            # Pour LOCATION
            if ctx['is_location']:
                # Caution
                ctx['has_caution'] = reservation.has_caution_payment()
                caution_paiement = paiements.filter(type_paiement='caution').first()
                ctx['caution_paiement'] = caution_paiement
                
                # Échéances
                echeances = reservation.echeances_loyer.all().order_by('numero_mois')
                ctx['echeances'] = echeances
                prochaines_echeances = []
                if ctx['has_caution']:
                    prochaines_client = get_next_echeances_a_payer(reservation.client)
                    prochaines_echeances = [
                        echeance for echeance in prochaines_client
                        if echeance.reservation_id == reservation.id
                    ]
                ctx['next_echeances'] = prochaines_echeances
                # Payées: statut_paiement == 'valide'
                ctx['echeances_payees'] = echeances.filter(statut_paiement=PaiementStatus.VALIDE)
                # En attente de validation: paiement enregistré mais statut 'enregistre'
                ctx['echeances_en_attente'] = echeances.filter(paiement__isnull=False, statut_paiement=PaiementStatus.ENREGISTRE)
                # Non payées: pas de paiement associé
                ctx['echeances_non_payees'] = echeances.filter(paiement__isnull=True)
                # Retard: parmi non payées, celles échues
                ctx['echeances_en_retard'] = [e for e in ctx['echeances_non_payees'] if e.is_en_retard()]
                
                # Montant loyer mensuel
                ctx['loyer_mensuel'] = unite.prix_ttc
            
            # Pour VENTE
            if ctx['is_vente']:
                ctx['prix_total'] = unite.prix_ttc
                ctx['montant_restant'] = unite.prix_ttc - ctx['total_paye']
                
                # Financement
                ctx['has_financement'] = hasattr(reservation, 'financement')
                if ctx['has_financement']:
                    ctx['financement'] = reservation.financement
        else:
            ctx['client'] = None
            ctx['message_info'] = "Aucune réservation active pour ce bien"
        
        return ctx


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboards/admin_dashboard.html'
    required_roles = ["ADMIN"]

    def get_context_data(self, **kwargs):
        from catalog.models import Programme, Unite
        from .models import Reservation, Paiement, Financement, Contrat
        from accounts.models import User, Role
        from django.db.models import Count, Q
        
        ctx = super().get_context_data(**kwargs)
        
        # Comptes principaux
        ctx["programmes_count"] = Programme.objects.count()
        ctx["unites_count"] = Unite.objects.count()
        ctx["reservations_count"] = Reservation.objects.count()
        ctx["paiements_count"] = Paiement.objects.count()
        
        # Comptes détaillés
        ctx["programmes_actifs"] = Programme.objects.filter(statut="actif").count()
        ctx["unites_disponibles"] = Unite.objects.filter(statut_disponibilite="disponible").count()
        ctx["reservations_confirmees"] = Reservation.objects.filter(statut="confirmee").count()
        ctx["paiements_valides"] = Paiement.objects.filter(statut="valide").count()
        
        # Comptes utilisateurs
        ctx["users_count"] = User.objects.count()
        ctx["clients_count"] = Client.objects.count()
        ctx["commercials_count"] = User.objects.filter(roles__code="COMMERCIAL").distinct().count()
        ctx["admins_count"] = User.objects.filter(roles__code="ADMIN").distinct().count()
        
        # Financements
        ctx["financements_count"] = Financement.objects.count()
        ctx["financements_acceptes"] = Financement.objects.filter(statut=FinancementStatus.ACCEPTE).count()
        ctx["financements_justificatif_soumis"] = Financement.objects.filter(statut=FinancementStatus.JUSTIFICATIF_SOUMIS).count()
        
        # Contrats et banques
        ctx["contrats_count"] = Contrat.objects.count()
        ctx["contrats_signes"] = Contrat.objects.filter(statut="signe").count()
        ctx["banques_count"] = BanquePartenaire.objects.count()
        
        # Listes détaillées avec select_related/prefetch_related
        ctx["programmes"] = Programme.objects.prefetch_related("unites").order_by("-created_at")[:10]
        ctx["derniers_paiements"] = Paiement.objects.select_related("reservation", "reservation__client").order_by("-date_paiement")[:10]
        ctx["dernieres_reservations"] = Reservation.objects.select_related("client", "unite", "unite__programme").prefetch_related("paiements", "documents").order_by("-created_at")[:10]
        
        return ctx


@method_decorator(login_required(login_url='login'), name='dispatch')
class StartReservationView(View):
    """Démarre le processus de réservation pour une unité avec upload documents."""

    def get(self, request, unite_id):
        unite = get_object_or_404(Unite, id=unite_id)
        # S'assurer que l'utilisateur a le rôle CLIENT
        role_client, _ = Role.objects.get_or_create(code="CLIENT", defaults={"libelle": "Client"})
        if not request.user.roles.filter(code="CLIENT").exists():
            request.user.roles.add(role_client)

        client, _ = Client.objects.get_or_create(
            user=request.user,
            defaults={
                "nom": request.user.last_name or request.user.email,
                "prenom": request.user.first_name or "",
                "telephone": "",
                "email": request.user.email,
            },
        )
        if request.method == "GET":
            form = ReservationForm()
        return render(request, "sales/reservation_form.html", {"form": form, "unite": unite, "client": client})

    def post(self, request, unite_id):
        unite = get_object_or_404(Unite, id=unite_id)
        client = request.user.client_profile
        form = ReservationForm(request.POST)
        
        if form.is_valid():
            # Créer la réservation
            reservation = form.save(commit=False)
            reservation.client = client
            reservation.unite = unite
            reservation.statut = "en_cours"  # Statut initial
            reservation.save()
            
            # Traiter les uploads de documents
            doc_types = {
                'document_cni': 'cni',
                'document_photo': 'photo',
                'document_residence': 'residence'
            }
            
            for field_name, doc_type in doc_types.items():
                if field_name in request.FILES:
                    fichier = request.FILES[field_name]
                    
                    # Valider fichier
                    if fichier.size > 5 * 1024 * 1024:  # 5MB
                        messages.error(request, f"Fichier {doc_type} trop volumineux (max 5MB)")
                        reservation.delete()
                        return render(request, "sales/reservation_form.html", {
                            "form": form, "unite": unite, "client": client
                        })
                    
                    if fichier.content_type not in ['application/pdf', 'image/jpeg', 'image/png']:
                        messages.error(request, f"Format non autorisé pour {doc_type}")
                        reservation.delete()
                        return render(request, "sales/reservation_form.html", {
                            "form": form, "unite": unite, "client": client
                        })
                    
                    # Créer le document
                    ReservationDocument.objects.create(
                        reservation=reservation,
                        document_type=doc_type,
                        fichier=fichier,
                        statut='en_attente'  # Commercial va valider
                    )
            
            # Mettre à jour le statut de l'unité à "réservé"
            unite.statut_disponibilite = "reserve"
            unite.save(update_fields=["statut_disponibilite"])
            
            # Log audit
            audit_log(request.user, reservation, "reservation_create", 
                     {"acompte": str(reservation.acompte), "documents": "3"}, request)
            
            messages.success(request, "✅ Réservation créée avec succès! Vos documents sont en attente de validation.")
            
            # Rediriger vers une page de confirmation
            return redirect("reservation_success", reservation_id=reservation.id)
        
        return render(request, "sales/reservation_form.html", {"form": form, "unite": unite, "client": client})


@method_decorator(login_required(login_url='login'), name='dispatch')
class PayReservationView(ReservationRequiredMixin, PaiementFormMixin, RoleRequiredMixin, View):
    required_roles = ["CLIENT"]

    def get(self, request, reservation_id):
        form = PaiementForm(initial={"montant": self.reservation.acompte or self.reservation.unite.prix_ttc})
        return render(request, "sales/paiement_form.html", {"form": form, "reservation": self.reservation})

    def post(self, request, reservation_id):
        form = PaiementForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.reservation = self.reservation
            paiement.source = "client"
            paiement.save()
            audit_log(request.user, paiement, "paiement_create", {"montant": str(paiement.montant)}, request)
            self.reservation.statut = "confirmee"
            self.reservation.save(update_fields=["statut"])
            return render(request, "sales/paiement_success.html", {"reservation": self.reservation, "paiement": paiement})
        return render(request, "sales/paiement_form.html", {"form": form, "reservation": self.reservation})


# 🏘️ CLIENT - Paiement d'une Échéance de Location
@method_decorator(login_required(login_url='login'), name='dispatch')
class ClientEchancePaiementView(RoleRequiredMixin, View):
    """Payer une échéance de loyer - CLIENT"""
    required_roles = ["CLIENT"]
    
    def get(self, request, echeance_id):
        """Afficher le formulaire de paiement d'échéance"""
        from .models import EcheanceLoyer
        
        client = request.user.client_profile
        echeance = get_object_or_404(
            EcheanceLoyer,
            id=echeance_id,
            reservation__client=client
        )
        
        # Pré-remplir le montant (lecture seule)
        reservation = echeance.reservation

        if echeance.is_payee():
            messages.info(request, "Cette échéance est déjà réglée.")
            return redirect('client_dashboard')

        if not reservation.has_caution_payment():
            messages.warning(
                request,
                "Veuillez d'abord payer la caution avant vos échéances mensuelles."
            )
            return redirect('client_caution_paiement', reservation_id=reservation.id)

        form = EcheancePaiementForm(initial={"montant": echeance.montant})
        
        context = {
            'echeance': echeance,
            'reservation': reservation,
            'form': form
        }
        return render(request, 'sales/client_echeance_paiement_form.html', context)
    
    def post(self, request, echeance_id):
        """Enregistrer le paiement d'une échéance"""
        from .models import EcheanceLoyer
        from core.choices import PaiementStatus, PaiementType
        
        client = request.user.client_profile
        echeance = get_object_or_404(
            EcheanceLoyer,
            id=echeance_id,
            reservation__client=client
        )

        reservation = echeance.reservation

        if echeance.is_payee():
            messages.info(request, "Cette échéance est déjà marquée comme payée.")
            return redirect('client_dashboard')

        if not reservation.has_caution_payment():
            messages.warning(
                request,
                "Vous devez régler la caution avant de payer vos échéances mensuelles."
            )
            return redirect('client_caution_paiement', reservation_id=reservation.id)
        
        form = EcheancePaiementForm(request.POST)
        if form.is_valid():
            paiement = Paiement.objects.create(
                reservation=reservation,
                montant=echeance.montant,
                moyen=form.cleaned_data['moyen'],
                type_paiement=PaiementType.ECHÉANCE_LOYER,
                statut=PaiementStatus.ENREGISTRE,
                source=form.cleaned_data['source'],
                notes=form.cleaned_data.get('notes', '')
            )

            echeance.paiement = paiement
            echeance.statut_paiement = PaiementStatus.ENREGISTRE
            echeance.save(update_fields=['paiement', 'statut_paiement'])
            
            # Audit log
            audit_log(request.user, paiement, 'echeance_paiement_client',
                     {'echeance_id': str(echeance_id), 'montant': str(paiement.montant)}, 
                     request)
            
            messages.success(request, f"Paiement d'échéance enregistré: {paiement.montant} FCFA")
            return render(request, 'sales/paiement_success.html', 
                          {'reservation': echeance.reservation, 'paiement': paiement, 'echeance': echeance})
        
        context = {
            'echeance': echeance,
            'reservation': reservation,
            'form': form
        }
        return render(request, 'sales/client_echeance_paiement_form.html', context)


@method_decorator(login_required(login_url='login'), name='dispatch')
class ClientCautionPaiementView(RoleRequiredMixin, View):
    """Permettre au client de payer la caution obligatoire"""
    required_roles = ["CLIENT"]

    def get_reservation(self, reservation_id):
        client = self.request.user.client_profile
        reservation = get_object_or_404(
            Reservation,
            id=reservation_id,
            client=client,
            unite__programme__type_operation=OperationType.LOCATION
        )
        return reservation

    def _redirect_if_already_paid(self, request, reservation):
        if reservation.has_caution_payment():
            messages.info(
                request,
                "La caution pour cette réservation est déjà enregistrée."
            )
            return redirect('client_dashboard')
        return None

    def get(self, request, reservation_id):
        reservation = self.get_reservation(reservation_id)
        redirect_response = self._redirect_if_already_paid(request, reservation)
        if redirect_response:
            return redirect_response

        try:
            montant_caution = calculer_montant_caution(reservation)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('client_dashboard')

        form = EcheancePaiementForm(initial={"montant": montant_caution})

        context = {
            'reservation': reservation,
            'form': form,
            'montant_caution': montant_caution,
        }
        return render(request, 'sales/client_caution_paiement_form.html', context)

    def post(self, request, reservation_id):
        reservation = self.get_reservation(reservation_id)
        redirect_response = self._redirect_if_already_paid(request, reservation)
        if redirect_response:
            return redirect_response

        try:
            montant_caution = calculer_montant_caution(reservation)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('client_dashboard')

        form = EcheancePaiementForm(request.POST)
        if form.is_valid():
            montant = montant_caution
            paiement = Paiement.objects.create(
                reservation=reservation,
                montant=montant,
                moyen=form.cleaned_data['moyen'],
                type_paiement=PaiementType.CAUTION,
                statut=PaiementStatus.ENREGISTRE,
                source=form.cleaned_data['source'],
                notes=form.cleaned_data.get('notes', '')
            )

            audit_log(request.user, paiement, 'caution_paiement_client',
                     {'reservation_id': str(reservation_id), 'montant': str(paiement.montant)},
                     request)

            messages.success(request, f"Caution enregistrée: {paiement.montant} FCFA")
            return render(
                request,
                'sales/paiement_success.html',
                {'reservation': reservation, 'paiement': paiement, 'is_caution': True}
            )
        else:
            # Debug: afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur {field}: {error}")

        context = {
            'reservation': reservation,
            'form': form,
            'montant_caution': montant_caution,
        }
        return render(request, 'sales/client_caution_paiement_form.html', context)


class ClientPayEcheanceView(RoleRequiredMixin, TemplateView):
    """Permettre au client de payer une échéance mensuelle"""
    template_name = 'sales/client_echéance_paiement_form.html'
    required_roles = ["CLIENT"]
    
    def get_echéance(self, echéance_id):
        from sales.models import EcheanceLoyer
        client = self.request.user.client_profile
        echeance = get_object_or_404(
            EcheanceLoyer,
            id=echéance_id,
            reservation__client=client
        )
        return echeance
    
    def get(self, request, echéance_id):
        echeance = self.get_echéance(echéance_id)
        
        # Vérifier que l'échéance n'est pas déjà payée
        if echeance.paiement and echeance.statut_paiement == PaiementStatus.VALIDE:
            messages.warning(request, "Cette échéance est déjà payée.")
            return redirect('client_reservation_detail', reservation_id=echeance.reservation.id)
        
        form = EcheancePaiementForm(initial={"montant": echeance.montant})
        
        context = {
            'echeance': echeance,
            'reservation': echeance.reservation,
            'form': form,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, echéance_id):
        echeance = self.get_echéance(echéance_id)
        reservation = echeance.reservation
        
        form = EcheancePaiementForm(request.POST)
        if form.is_valid():
            # Créer le paiement
            paiement = Paiement.objects.create(
                reservation=reservation,
                montant=echeance.montant,
                moyen=form.cleaned_data['moyen'],
                type_paiement=PaiementType.ECHÉANCE_LOYER,
                statut=PaiementStatus.ENREGISTRE,
                source=form.cleaned_data['source'],
                notes=form.cleaned_data.get('notes', '')
            )
            
            # Lier le paiement à l'échéance
            echeance.paiement = paiement
            echeance.save(update_fields=['paiement'])
            
            audit_log(request.user, paiement, 'echeance_paiement_client',
                     {'echéance_id': str(echéance_id), 'montant': str(paiement.montant)},
                     request)
            
            messages.success(request, f"Échéance enregistrée: {paiement.montant} FCFA")
            return render(
                request,
                'sales/paiement_success.html',
                {'reservation': reservation, 'paiement': paiement, 'is_echeance': True}
            )
        else:
            # Afficher les erreurs
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur {field}: {error}")
        
        context = {
            'echeance': echeance,
            'reservation': reservation,
            'form': form,
        }
        return render(request, self.template_name, context)


def start_reservation_or_auth(request, unite_id):
    """Si non connecté, on stocke l'unité en session et on envoie vers login/register."""
    if not request.user.is_authenticated:
        set_pending_unite(request, unite_id)
        return redirect("login")
    return redirect("start_reservation", unite_id=unite_id)


@method_decorator(login_required(login_url='login'), name='dispatch')
class ReservationSuccessView(RoleRequiredMixin, TemplateView):
    """
    Page de confirmation après réservation.
    Affiche les prochaines étapes : financement, contrat, paiement
    """
    template_name = 'sales/reservation_success.html'
    required_roles = ["CLIENT"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        client = get_object_or_404(Client, user=self.request.user)
        
        reservation = get_object_or_404(Reservation, id=reservation_id, client=client)
        ctx['reservation'] = reservation
        ctx['banques'] = BanquePartenaire.objects.all()
        
        # Calculer le montant restant à financer
        prix_total = reservation.unite.prix_ttc
        acompte = reservation.acompte or 0
        
        # Soustraire les paiements validés déjà effectués
        paiements_valides = Paiement.objects.filter(
            reservation=reservation,
            statut='valide'
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        ctx['remaining_amount'] = prix_total - acompte - paiements_valides
        
        return ctx


@method_decorator(login_required(login_url='login'), name='dispatch')
class ClientReservationDetailView(RoleRequiredMixin, TemplateView):
    """
    Détail d'une réservation côté client.
    Affiche le résumé, l'historique et les actions possibles
    """
    template_name = 'sales/client_reservation_detail.html'
    required_roles = ["CLIENT"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        client = get_object_or_404(Client, user=self.request.user)
        
        # Vérifier que la réservation appartient au client
        reservation = get_object_or_404(Reservation, id=reservation_id, client=client)
        
        ctx['reservation'] = reservation
        ctx['banques'] = BanquePartenaire.objects.all()
        
        # Vérifier les statuts et actions disponibles
        ctx['has_financement'] = hasattr(reservation, 'financement')
        ctx['has_contrat'] = hasattr(reservation, 'contrat')
        ctx['paiements'] = reservation.paiements.all()
        ctx['total_payes'] = sum(p.montant for p in ctx['paiements'] if p.statut == 'valide')
        ctx['montant_restant'] = reservation.unite.prix_ttc - ctx['total_payes']
        
        # Échéances de loyer : n'afficher que la prochaine (et éventuellement la suivante après le 27)
        ctx['echéances'] = []
        if reservation.is_location() and reservation.has_caution_payment():
            prochaine_echeances = get_next_echeances_a_payer(client)
            ctx['echéances'] = [
                echeance for echeance in prochaine_echeances
                if echeance.reservation_id == reservation.id
            ]
        
        # Date du jour pour vérifier les retards
        from datetime import date
        ctx['today'] = date.today()
        
        # Documents
        ctx['documents'] = reservation.documents.all()
        documents_valides = reservation.documents.filter(statut='valide').count()
        documents_rejetes = reservation.documents.filter(statut='rejete').count()
        ctx['documents_valides'] = documents_valides == 3  # Tous 3 docs valides
        ctx['documents_rejetes'] = documents_rejetes > 0
        ctx['missing_documents'] = ReservationDocumentService.get_missing_documents(reservation)
        
        # OTP Data for contract signing
        if ctx['has_contrat']:
            contrat = reservation.contrat
            if SignatureService.otp_exists(contrat):
                ctx['contrat_otp'] = SignatureService.get_otp(contrat)
                ctx['otp_remaining'] = SignatureService.get_otp_remaining_time(contrat)
        
        # Suivi Chantier (seulement si contrat signé)
        ctx['contrat_signe'] = False
        ctx['avancements_chantier'] = []
        if ctx['has_contrat'] and reservation.contrat.statut == 'signe':
            ctx['contrat_signe'] = True
            # Récupérer les avancements de l'unité
            from catalog.models import AvancementChantierUnite
            ctx['avancements_chantier'] = AvancementChantierUnite.objects.filter(
                unite=reservation.unite
            ).select_related('unite', 'reservation').prefetch_related('photos').order_by('-date_pointage')[:5]
        
        return ctx


class DashboardAdminView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "sales/admin_dashboard.html"

    def test_func(self):
        """
        Autoriser :
        - admin scindongo
        - superuser
        """
        u = self.request.user
        return bool(u and u.is_authenticated and is_admin_user(u))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Stats globales
        total_programmes = Programme.objects.count()
        total_reservations = Reservation.objects.count()
        reservations_confirmees = Reservation.objects.filter(statut="confirmee").count()

        unites_disponibles = Unite.objects.filter(statut_disponibilite="disponible").count()
        unites_reservees = Unite.objects.filter(statut_disponibilite="reserve").count()
        # Si le statut "vendu" n'existe pas encore, ça retournera simplement 0
        unites_vendues = Unite.objects.filter(statut_disponibilite="vendu").count()

        total_paiements_valides = (
            Paiement.objects.filter(statut="valide").aggregate(total=Sum("montant"))["total"] or 0
        )

        # Listes récentes
        reservations_recent = (
            Reservation.objects.select_related("client", "unite")
            .order_by("-created_at")[:5]
        )
        paiements_recents = (
            Paiement.objects.select_related("reservation")
            .order_by("-created_at")[:5]
        )
        financements_recents = (
            Financement.objects.select_related("banque", "reservation")
            .order_by("-created_at")[:5]
        )
        banques = BanquePartenaire.objects.all().order_by("nom")[:10]

        context.update(
            {
                "total_programmes": total_programmes,
                "total_reservations": total_reservations,
                "reservations_confirmees": reservations_confirmees,
                "unites_disponibles": unites_disponibles,
                "unites_reservees": unites_reservees,
                "unites_vendues": unites_vendues,
                "total_paiements_valides": total_paiements_valides,
                "reservations_recent": reservations_recent,
                "paiements_recents": paiements_recents,
                "financements_recents": financements_recents,
                "banques": banques,
            }
        )
        return context


# ============================================================================
# COMMERCIAL ACTIONS - Gestion des clients, réservations, financements, etc.
# ============================================================================

class CommercialReservationConfirmView(RoleRequiredMixin, CommercialReservationAccessMixin, TemplateView):
    """
    Vue pour que le commercial CONFIRME une réservation (en_cours → confirmée)
    Avant confirmation, vérifier la KYC du client
    """
    template_name = 'sales/commercial_reservation_confirm.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        
        ctx['reservation'] = reservation
        ctx['client'] = reservation.client
        ctx['unite'] = reservation.unite
        
        return ctx
    
    def post(self, request, reservation_id):
        """Valider la réservation"""
        reservation = self.get_reservation()
        
        # Vérifier que la réservation est bien en "en_cours"
        if reservation.statut != "en_cours":
            messages.error(request, "Cette réservation ne peut pas être confirmée")
            return redirect('commercial_reservation_detail', reservation_id=reservation_id)
        
        # Changer le statut à "confirmée"
        reservation.statut = "confirmee"
        reservation.save(update_fields=['statut'])
        
        messages.success(request, f"Réservation de {reservation.client.prenom} {reservation.client.nom} confirmée !")
        audit_log(request.user, reservation, "reservation_confirm", {"ancien_statut": "en_cours"}, request)
        
        return redirect('commercial_reservation_detail', reservation_id=reservation_id)


class CommercialClientListView(RoleRequiredMixin, ListView):
    """Liste des clients (filtrée par commercial)"""
    model = Client
    template_name = 'sales/commercial_client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    required_roles = ["COMMERCIAL"]
    
    def get_queryset(self):
        user = self.request.user
        qs = Client.objects.select_related('user').order_by('-created_at')
        
        # 🔒 ADMIN voit tous les clients, COMMERCIAL seulement les siens
        if is_admin_user(user):
            return qs
        
        # Clients ayant réservé sur MES programmes
        return qs.filter(
            reservations__unite__programme__contact_commercial=user
        ).distinct()


class CommercialClientCreateView(RoleRequiredMixin, CreateView):
    """Créer un nouveau client"""
    model = Client
    form_class = ClientForm
    template_name = 'sales/commercial_client_form.html'
    required_roles = ["COMMERCIAL"]
    success_url = reverse_lazy('commercial_client_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Client {self.object.nom} créé avec succès")
        audit_log(self.request.user, self.object, "client_create", {"nom": self.object.nom}, self.request)
        return response


class CommercialClientUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier un client"""
    model = Client
    form_class = ClientForm
    template_name = 'sales/commercial_client_form.html'
    required_roles = ["COMMERCIAL"]
    success_url = reverse_lazy('commercial_client_list')
    
    def get_queryset(self):
        user = self.request.user
        qs = Client.objects.all()
        
        # 🔒 ADMIN voit tous les clients, COMMERCIAL seulement les siens
        if is_admin_user(user):
            return qs
        
        # Clients ayant réservé sur MES programmes
        return qs.filter(
            reservations__unite__programme__contact_commercial=user
        ).distinct()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Client {self.object.nom} mis à jour")
        audit_log(self.request.user, self.object, "client_update", {"nom": self.object.nom}, self.request)
        return response


class CommercialReservationListView(RoleRequiredMixin, ListView):
    """Liste des réservations (filtrée par commercial)"""
    model = Reservation
    template_name = 'sales/commercial_reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    required_roles = ["COMMERCIAL"]
    
    def get_queryset(self):
        user = self.request.user
        qs = Reservation.objects.select_related('client', 'unite', 'unite__programme').order_by('-created_at')
        
        # 🔒 ADMIN voit toutes les réservations, COMMERCIAL seulement les siennes
        if is_admin_user(user):
            return qs
        
        # Seulement les réservations sur MES programmes
        return qs.filter(unite__programme__contact_commercial=user)


class CommercialReservationDetailView(RoleRequiredMixin, CommercialReservationAccessMixin, TemplateView):
    """Détail d'une réservation avec actions possibles + documents + messages"""
    template_name = 'sales/commercial_reservation_detail.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        ctx['reservation'] = reservation
        ctx['documents'] = reservation.documents.all()
        ctx['banques'] = BanquePartenaire.objects.all()
        
        # Statuts possibles suivants
        ctx['can_add_financement'] = not hasattr(reservation, 'financement')
        ctx['can_sign_contrat'] = not hasattr(reservation, 'contrat')
        ctx['can_add_paiement'] = True
        
        # Documents status
        can_reserve, msg = ReservationDocumentService.can_make_reservation(reservation)
        ctx['all_documents_valid'] = can_reserve
        ctx['missing_documents'] = ReservationDocumentService.get_missing_documents(reservation)
        
        # Vérifier si tous les docs sont validés
        all_valid = reservation.documents.filter(statut='valide').count() == 3
        ctx['documents_complete'] = all_valid
        
        # OTP Data for contract signing
        if hasattr(reservation, 'contrat'):
            contrat = reservation.contrat
            ctx['contrat_otp_exists'] = SignatureService.otp_exists(contrat)
            ctx['contrat_is_blocked'] = SignatureService.is_contrat_blocked(contrat)
            ctx['contrat_otp_remaining'] = SignatureService.get_otp_remaining_time(contrat) if ctx['contrat_otp_exists'] else None
        
        return ctx
    
    def post(self, request, *args, **kwargs):
        """Traiter les actions (validation doc, message, etc)"""
        action = request.POST.get('action')
        reservation = self.get_reservation()
        
        if action == 'validate_document':
            document_id = request.POST.get('document_id')
            doc = get_object_or_404(ReservationDocument, id=document_id)
            
            doc.statut = 'valide'
            doc.verifie_par = request.user
            doc.verifie_le = timezone.now()
            doc.save()
            
            messages.success(request, f"✅ Document '{doc.get_document_type_display()}' validé")
            audit_log(request.user, doc, 'document_validated', {'document_type': doc.document_type}, request)
        
        elif action == 'reject_document':
            document_id = request.POST.get('document_id')
            raison = request.POST.get('raison_rejet', '')
            doc = get_object_or_404(ReservationDocument, id=document_id)
            
            doc.statut = 'rejete'
            doc.raison_rejet = raison
            doc.verifie_par = request.user
            doc.verifie_le = timezone.now()
            doc.save()
            
            messages.warning(request, f"❌ Document '{doc.get_document_type_display()}' rejeté")
            audit_log(request.user, doc, 'document_rejected', {'reason': raison}, request)
        
        elif action == 'send_message':
            message_text = request.POST.get('message', '').strip()
            if message_text:
                # TODO: Créer un modèle Message si besoin
                # Pour maintenant, on peut envoyer un email
                messages.success(request, f"✉️ Message envoyé au client")
                audit_log(request.user, reservation, 'message_sent_to_client', {'message': message_text[:50]}, request)
            else:
                messages.error(request, "Le message ne peut pas être vide")
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)


class CommercialFinancementCreateView(RoleRequiredMixin, CommercialReservationAccessMixin, CreateView):
    """Créer un financement pour une réservation"""
    model = Financement
    form_class = FinancementForm
    template_name = 'sales/commercial_financement_form.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        ctx['reservation'] = reservation
        return ctx
    
    def form_valid(self, form):
        reservation = self.get_reservation()
        
        # Vérifier qu'il n'y a pas déjà un financement
        if hasattr(reservation, 'financement'):
            messages.error(self.request, "Un financement existe déjà pour cette réservation")
            return self.form_invalid(form)
        
        financement = form.save(commit=False)
        financement.reservation = reservation
        financement.statut = FinancementStatus.JUSTIFICATIF_SOUMIS
        financement.save()
        
        messages.success(self.request, "Financement créé.")
        audit_log(self.request.user, financement, "financement_create", 
                 {"banque": financement.banque.nom, "montant": str(financement.montant)}, self.request)
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        reservation = self.get_reservation()
        # Pré-remplir le montant avec le prix de l'unité
        kwargs['initial'] = {'montant': reservation.unite.prix_ttc}
        return kwargs


class CommercialFinancementUpdateView(RoleRequiredMixin, CommercialReservationAccessMixin, UpdateView):
    """Mettre à jour le statut d'un financement"""
    model = Financement
    fields = ['statut']
    template_name = 'sales/commercial_financement_update.html'
    required_roles = ["COMMERCIAL"]
    
    def get_object(self):
        reservation = self.get_reservation()
        return get_object_or_404(Financement, reservation=reservation)
    
    def get_success_url(self):
        return reverse_lazy('commercial_reservation_detail', kwargs={'reservation_id': self.object.reservation.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Financement mis à jour: {self.object.get_statut_display()}")
        audit_log(self.request.user, self.object, "financement_update", 
                 {"statut": self.object.statut}, self.request)
        return response


class CommercialContratCreateView(RoleRequiredMixin, CommercialReservationAccessMixin, CreateView):
    """Créer un contrat pour une réservation"""
    model = Contrat
    form_class = ContratForm
    template_name = 'sales/commercial_contrat_form.html'
    required_roles = ["COMMERCIAL"]
    
    def _default_conditions_generales(self, reservation):
        programme_nom = reservation.unite.programme.nom
        unite_ref = reservation.unite.reference_lot
        return (
            "Le présent contrat formalise la réservation du bien indiqué ci-dessous au sein du programme "
            f"{programme_nom}. Le client reconnaît avoir pris connaissance des descriptifs techniques du lot {unite_ref} "
            "et s'engage à respecter le calendrier de paiement convenu avec SCINDONGO Immo. Toute modification ou avenant "
            "doit être validé par écrit par les deux parties."
        )

    def _default_conditions_particulieres(self, reservation, end_date):
        duree = reservation.duree_bail_mois or 12
        montant = number_format(reservation.unite.prix_ttc, decimal_pos=0, force_grouping=True)
        date_fin_str = end_date.strftime("%d/%m/%Y") if end_date else "-"
        return (
            f"• Durée contractuelle : {duree} mois, renouvelable d'un commun accord.\n"
            f"• Montant total TTC : {montant} FCFA (hors frais de dossier et taxes).\n"
            f"• Mise à disposition et livraison prévues au plus tard le {date_fin_str}, sous réserve de l'avancement du chantier.\n"
            "• Les charges de copropriété, taxes et assurances restent à la charge du client."
        )

    def _build_initial_payload(self, reservation):
        client = reservation.client
        unite = reservation.unite
        programme = unite.programme
        commercial = programme.contact_commercial
        today = timezone.localdate()
        duree = reservation.duree_bail_mois or 12
        end_date = today + relativedelta(months=duree)

        return {
            'client_nom': f"{client.prenom} {client.nom}".strip(),
            'client_email': client.email,
            'client_telephone': client.telephone,
            'client_adresse': '',
            'programme_nom': programme.nom,
            'unite_reference': unite.reference_lot,
            'unite_description': unite.modele_bien.nom_marketing,
            'montant_total': unite.prix_ttc,
            'date_signature': today,
            'date_fin': end_date,
            'lieu_signature': getattr(settings, 'COMPANY_CITY', 'Dakar'),
            'commercial_nom': (commercial.get_full_name() if commercial else '') or (commercial.email if commercial else ''),
            'commercial_email': commercial.email if commercial else '',
            'conditions_generales': self._default_conditions_generales(reservation),
            'conditions_particulieres': self._default_conditions_particulieres(reservation, end_date),
            'statut': ContratStatus.BROUILLON,
        }

    def get_initial(self):
        initial = super().get_initial()
        reservation = self.get_reservation()
        initial.update(self._build_initial_payload(reservation))
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        initial_payload = self._build_initial_payload(reservation)
        ctx['reservation'] = reservation
        ctx['contrat'] = None
        ctx['is_update'] = False
        programme = reservation.unite.programme
        ctx['operation_type_code'] = programme.type_operation
        ctx['operation_type_label'] = programme.get_type_operation_display()
        ctx['is_location_operation'] = reservation.is_location()
        ctx['caution_amount'] = (
            calculer_montant_caution(reservation)
            if ctx['is_location_operation'] else None
        )
        ctx['contrat_preview'] = {
            'numero': f"CTR-{reservation.id}-{timezone.localdate().strftime('%Y%m%d')}",
            'statut': ContratStatus.BROUILLON.label,
            'date_signature': initial_payload.get('date_signature'),
            'date_fin': initial_payload.get('date_fin'),
        }
        ctx['contrat_display'] = {
            'numero': ctx['contrat_preview']['numero'],
            'statut': ctx['contrat_preview']['statut'],
            'date_signature': ctx['contrat_preview']['date_signature'],
        }
        ctx['initial_payload'] = initial_payload
        return ctx
    
    def form_valid(self, form):
        reservation = self.get_reservation()
        
        # Vérifier qu'il n'y a pas déjà un contrat
        if hasattr(reservation, 'contrat'):
            messages.error(self.request, "Un contrat existe déjà pour cette réservation")
            return self.form_invalid(form)
        
        action = self.request.POST.get('action', 'generate')
        contrat = form.save(commit=False)
        contrat.reservation = reservation
        contrat.numero = f"CTR-{reservation.id}-{timezone.localdate().strftime('%Y%m%d')}"
        contrat.statut = ContratStatus.BROUILLON
        contrat.duree_mois = reservation.duree_bail_mois or contrat.duree_mois or 12
        if not contrat.date_signature:
            contrat.date_signature = timezone.localdate()
        if not contrat.date_fin and contrat.date_signature and contrat.duree_mois:
            contrat.date_fin = contrat.date_signature + relativedelta(months=contrat.duree_mois)
        contrat.generated_pdf = False
        contrat.save()

        pdf_uploaded = bool(form.cleaned_data.get('pdf'))
        if not pdf_uploaded or action == 'generate':
            generate_contract_pdf(contrat, self.request.user)
            messages.success(
                self.request,
                f"Contrat {contrat.numero} créé et PDF généré automatiquement. L'OTP peut être envoyé.",
            )
        else:
            messages.success(
                self.request,
                f"Contrat {contrat.numero} créé avec votre document PDF.",
            )

        audit_log(
            self.request.user,
            contrat,
            "contrat_create",
            {"numero": contrat.numero, "auto_pdf": (not pdf_uploaded or action == 'generate')},
            self.request,
        )
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)


class CommercialContratUpdateView(RoleRequiredMixin, CommercialReservationAccessMixin, UpdateView):
    """Mettre à jour ou régénérer un contrat"""
    model = Contrat
    form_class = ContratForm
    template_name = 'sales/commercial_contrat_form.html'
    required_roles = ["COMMERCIAL"]
    
    def get_object(self):
        reservation = self.get_reservation()
        return get_object_or_404(Contrat, reservation=reservation)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        ctx['reservation'] = reservation
        ctx['contrat'] = self.object
        ctx['is_update'] = True
        programme = reservation.unite.programme
        ctx['operation_type_code'] = programme.type_operation
        ctx['operation_type_label'] = programme.get_type_operation_display()
        ctx['is_location_operation'] = reservation.is_location()
        ctx['caution_amount'] = (
            calculer_montant_caution(reservation)
            if ctx['is_location_operation'] else None
        )
        ctx['contrat_preview'] = None
        ctx['contrat_display'] = {
            'numero': self.object.numero,
            'statut': self.object.get_statut_display(),
            'date_signature': self.object.date_signature,
        }
        return ctx
    
    def get_success_url(self):
        return reverse_lazy('commercial_reservation_detail', kwargs={'reservation_id': self.object.reservation.id})
    
    def form_valid(self, form):
        action = self.request.POST.get('action', 'save')
        uploaded_pdf = bool(form.cleaned_data.get('pdf'))
        self.object = form.save()

        regenerate = action == 'regenerate' or (not uploaded_pdf and not self.object.pdf)
        if uploaded_pdf and action != 'regenerate':
            self.object.generated_pdf = False
            self.object.save(update_fields=['generated_pdf'])

        if regenerate:
            generate_contract_pdf(self.object, self.request.user)
            regen_msg = " et le PDF a été régénéré automatiquement"
        else:
            regen_msg = ""

        messages.success(
            self.request,
            f"Contrat mis à jour{regen_msg}. Statut actuel : {self.object.get_statut_display()}"
        )
        audit_log(
            self.request.user,
            self.object,
            "contrat_update",
            {"statut": self.object.statut, "regenerated": regenerate},
            self.request,
        )
        return redirect(self.get_success_url())


class CommercialPaiementCreateView(RoleRequiredMixin, CommercialReservationAccessMixin, CreateView):
    """Créer un paiement pour une réservation"""
    model = Paiement
    form_class = PaiementForm
    template_name = 'sales/commercial_paiement_form.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = self.get_reservation()
        ctx['reservation'] = reservation
        return ctx
    
    def form_valid(self, form):
        reservation = self.get_reservation()
        
        paiement = form.save(commit=False)
        paiement.reservation = reservation
        paiement.statut = "valide"  # Le commercial valide directement
        paiement.save()
        
        messages.success(self.request, f"Paiement de {paiement.montant} enregistré et validé")
        audit_log(self.request.user, paiement, "paiement_create", 
                 {"montant": str(paiement.montant), "moyen": paiement.moyen}, self.request)
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)


# 🏘️ COMMERCIAL - Paiement d'une Échéance de Location
class CommercialEchancePaiementView(RoleRequiredMixin, View):
    """Enregistrer et valider un paiement d'échéance - COMMERCIAL"""
    required_roles = ["COMMERCIAL", "ADMIN"]
    
    def get_reservation(self):
        """Helper pour vérifier l'accès"""
        from .models import EcheanceLoyer
        
        echeance_id = self.kwargs['echeance_id']
        echeance = get_object_or_404(EcheanceLoyer, id=echeance_id)
        reservation = echeance.reservation
        
        # Vérifier l'accès
        user = self.request.user
        if not is_admin_user(user):
            if reservation.unite.programme.contact_commercial != user:
                raise PermissionDenied()
        
        return reservation, echeance
    
    def get(self, request, echeance_id):
        """Afficher le formulaire de paiement d'échéance"""
        reservation, echeance = self.get_reservation()
        
        if echeance.is_payee():
            messages.info(request, "Cette échéance est déjà réglée.")
            return redirect('commercial_dashboard')

        if not reservation.has_caution_payment():
            messages.warning(
                request,
                "La caution doit être enregistrée avant d'encaisser les échéances mensuelles."
            )
            return redirect('commercial_dashboard')

        # Pré-remplir le montant (lecture seule)
        form = EcheancePaiementForm(initial={"montant": echeance.montant})
        
        context = {
            'echeance': echeance,
            'reservation': reservation,
            'form': form
        }
        return render(request, 'sales/commercial_echeance_paiement_form.html', context)
    
    def post(self, request, echeance_id):
        """Enregistrer et valider le paiement d'une échéance"""
        from core.choices import PaiementStatus, PaiementType
        
        reservation, echeance = self.get_reservation()
        
        if echeance.is_payee():
            messages.info(request, "Cette échéance est déjà réglée.")
            return redirect('commercial_dashboard')

        if not reservation.has_caution_payment():
            messages.warning(
                request,
                "Merci d'enregistrer la caution avant de valider les échéances."
            )
            return redirect('commercial_dashboard')

        form = EcheancePaiementForm(request.POST)
        if form.is_valid():
            paiement = Paiement.objects.create(
                reservation=reservation,
                montant=echeance.montant,
                moyen=form.cleaned_data['moyen'],
                type_paiement=PaiementType.ECHÉANCE_LOYER,
                statut=PaiementStatus.VALIDE,
                source=form.cleaned_data['source'],
                notes=form.cleaned_data.get('notes', '')
            )

            echeance.paiement = paiement
            echeance.statut_paiement = PaiementStatus.VALIDE
            echeance.save(update_fields=['paiement', 'statut_paiement'])

            audit_log(request.user, paiement, 'echeance_paiement_commercial',
                     {'echeance_id': str(echeance_id), 'montant': str(paiement.montant)},
                     request)

            messages.success(request, f'Paiement d\'échéance validé: {paiement.montant} FCFA')
            return redirect('commercial_dashboard')

        context = {
            'echeance': echeance,
            'reservation': reservation,
            'form': form
        }
        return render(request, 'sales/commercial_echeance_paiement_form.html', context)



# ÉTAPE 5: Client choose payment mode (Direct vs Financing)
class ClientPaymentModeChoiceView(RoleRequiredMixin, TemplateView):
    """ÉTAPE 5: Client choisit le mode de paiement après confirmation (VENTE SEULEMENT)"""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_payment_mode_choice.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Valider que VENTE avant tout traitement"""
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=request.user)
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except (Client.DoesNotExist, Reservation.DoesNotExist):
            raise Http404("Réservation non trouvée")
        
        # 🔴 LOCATION: Rediriger
        if reservation.is_location():
            if not reservation.has_caution_payment():
                messages.info(
                    request,
                    "⚠️ Pour une location, vous devez d'abord payer la caution (2 mois de loyer)."
                )
                return redirect('client_caution_paiement', reservation_id=reservation.id)
            else:
                messages.info(
                    request,
                    "ℹ️ Pour une location, les paiements se font directement. "
                    "Consultez vos échéances dans votre tableau de bord."
                )
                return redirect('client_dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """GET: Contexte pour le formulaire de choix"""
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=self.request.user)
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except (Client.DoesNotExist, Reservation.DoesNotExist):
            raise Http404("Réservation non trouvée")
        
        ctx['reservation'] = reservation
        ctx['unite'] = reservation.unite
        ctx['remaining_amount'] = reservation.unite.prix_ttc - reservation.acompte
        ctx['form'] = PaymentModeForm()
        ctx['is_vente'] = reservation.is_vente()
        
        # Pour LOCATION: ajouter le montant de caution
        if reservation.is_location():
            from .utils import calculer_montant_caution
            ctx['caution_amount'] = calculer_montant_caution(reservation)
        
        return ctx
    
    def post(self, request, *args, **kwargs):
        """POST: Traiter le choix de mode de paiement"""
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=request.user)
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except (Client.DoesNotExist, Reservation.DoesNotExist):
            raise Http404("Réservation non trouvée")
        
        # 🔴 Vérification supplémentaire: VENTE uniquement
        if not reservation.is_vente():
            messages.error(request, "Choix de paiement réservé aux ventes.")
            return redirect('client_dashboard')
        
        form = PaymentModeForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulaire invalide. Veuillez réessayer.")
            return self.get(request, *args, **kwargs)
        
        payment_mode = form.cleaned_data['payment_mode']
        
        if payment_mode == 'direct':
            return redirect('client_direct_payment', reservation_id=reservation_id)
        else:  # financing
            return redirect('client_financing_request', reservation_id=reservation_id)


# ÉTAPE 6: Direct Payment View
class ClientDirectPaymentView(RoleRequiredMixin, TemplateView):
    """ÉTAPE 6: Client fait un paiement direct (virement, chèque, espèces, carte) - VENTE UNIQUEMENT"""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_direct_payment.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Vérifier que VENTE avant le traitement"""
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=request.user)
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except (Client.DoesNotExist, Reservation.DoesNotExist):
            raise Http404("Réservation non trouvée")
        
        # 🔴 LOCATION: Bloquer
        if not reservation.is_vente():
            messages.error(
                request,
                "⚠️ Le paiement direct n'est disponible que pour les ventes."
            )
            return redirect('client_dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=self.request.user)
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except (Client.DoesNotExist, Reservation.DoesNotExist):
            raise Http404("Réservation introuvable")
        
        ctx['reservation'] = reservation
        ctx['unite'] = reservation.unite
        ctx['remaining_amount'] = reservation.unite.prix_ttc - reservation.acompte
        ctx['form'] = PaiementForm()
        return ctx
    
    def post(self, request, reservation_id):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            raise Http404("Pas de profil Client trouvé")
        
        try:
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except Reservation.DoesNotExist:
            raise Http404("Réservation introuvable")
        
        # 🔴 LOCATION : Bloquer l'accès au paiement direct
        if reservation.is_location():
            messages.error(
                request,
                "⚠️ Le paiement direct n'est pas disponible pour les locations. "
                "Utilisez le système de caution et d'échéances."
            )
            return redirect('client_dashboard')
        
        form = PaiementForm(request.POST)
        if not form.is_valid():
            # Re-render the form with errors
            context = self.get_context_data(reservation_id=reservation_id)
            context['form'] = form
            return self.render_to_response(context)
        
        paiement = form.save(commit=False)
        paiement.reservation = reservation
        paiement.statut = 'enregistre'  # Pending commercial validation
        
        # Validation: montant ne peut pas dépasser le montant restant
        max_amount = reservation.unite.prix_ttc - reservation.acompte
        if paiement.montant > max_amount:
            form.add_error('montant', f'Montant maximum : {max_amount} FCFA')
            context = self.get_context_data(reservation_id=reservation_id)
            context['form'] = form
            return self.render_to_response(context)
        
        paiement.save()
        
        # Audit log
        audit_log(
            request.user,
            paiement,
            'direct_payment_request',
            {
                'montant': str(paiement.montant),
                'moyen': paiement.moyen,
                'statut': 'enregistre'
            },
            request
        )
        
        messages.success(
            request,
            f"✅ Paiement de {paiement.montant} FCFA enregistré ! "
            "Le commercial validera votre paiement dans les 24h."
        )
        
        return redirect('client_reservation_detail', reservation_id=reservation_id)


# ÉTAPE 7: Financing Request View
class ClientFinancingRequestView(RoleRequiredMixin, TemplateView):
    """Client soumet directement le justificatif de financement bancaire (VENTE uniquement)."""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_financing_request.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Vérifier que VENTE avant le traitement"""
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=request.user)
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except (Client.DoesNotExist, Reservation.DoesNotExist):
            raise Http404("Réservation non trouvée")
        
        # 🔴 LOCATION: Bloquer
        if not reservation.is_vente():
            messages.error(
                request,
                "⚠️ Le financement bancaire n'est disponible que pour les ventes."
            )
            return redirect('client_dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        
        try:
            client = Client.objects.get(user=self.request.user)
        except Client.DoesNotExist:
            raise Http404("Pas de profil Client trouvé")
        
        try:
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except Reservation.DoesNotExist:
            raise Http404("Réservation introuvable")
        
        ctx['reservation'] = reservation
        ctx['unite'] = reservation.unite
        
        # Calculer le montant restant à financer
        prix_total = reservation.unite.prix_ttc
        acompte = reservation.acompte or 0
        
        # Soustraire les paiements validés déjà effectués
        paiements_valides = Paiement.objects.filter(
            reservation=reservation,
            statut='valide'
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        ctx['remaining_amount'] = prix_total - acompte - paiements_valides
        ctx['banks'] = BanquePartenaire.objects.all()

        # Import form here to avoid circular imports
        from .forms import FinancingRequestForm
        ctx['form'] = FinancingRequestForm()

        return ctx
    
    def post(self, request, reservation_id):
        from .forms import FinancingRequestForm
        
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            raise Http404("Pas de profil Client trouvé")
        
        try:
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except Reservation.DoesNotExist:
            raise Http404("Réservation introuvable")
        
        form = FinancingRequestForm(request.POST, request.FILES)
        if not form.is_valid():
            context = self.get_context_data(reservation_id=reservation_id)
            context['form'] = form
            return self.render_to_response(context)
        
        # Empêcher la création d'un financement en double pour la même réservation
        financement, created = Financement.objects.get_or_create(
            reservation=reservation,
            defaults={
                'banque': form.cleaned_data['banque'],
                'montant': form.cleaned_data['montant'],
                'justificatif_financement': form.cleaned_data['justificatif_financement'],
                'statut': FinancementStatus.JUSTIFICATIF_SOUMIS,
            }
        )
        if not created:
            # Mise à jour si déjà existant
            financement.banque = form.cleaned_data['banque']
            financement.montant = form.cleaned_data['montant']
            financement.justificatif_financement = form.cleaned_data['justificatif_financement']
            financement.statut = FinancementStatus.JUSTIFICATIF_SOUMIS
        # Validation: montant ne peut pas dépasser le montant restant
        prix_total = reservation.unite.prix_ttc
        acompte = reservation.acompte or 0
        paiements_valides = Paiement.objects.filter(
            reservation=reservation,
            statut='valide'
        ).aggregate(total=Sum('montant'))['total'] or 0
        max_amount = prix_total - acompte - paiements_valides
        if financement.montant > max_amount:
            form.add_error('montant', f'Montant maximum : {max_amount} FCFA')
            context = self.get_context_data(reservation_id=reservation_id)
            context['form'] = form
            return self.render_to_response(context)
        financement.save()
        
        # Audit log
        audit_log(
            request.user,
            financement,
            'financing_justificatif_submitted',
            {
                'montant': str(financement.montant),
                'banque': str(financement.banque),
                'statut': FinancementStatus.JUSTIFICATIF_SOUMIS
            },
            request
        )
        
        messages.success(
            request,
            "✅ Document soumis avec succès."
        )

        return redirect('client_reservation_detail', reservation_id=reservation_id)


# ÉTAPE 8: Commercial Payment Validation View
class CommercialPaymentValidationListView(RoleRequiredMixin, ListView):
    """ÉTAPE 8: Commercial valide les paiements enregistrés"""
    required_roles = ["COMMERCIAL"]
    model = Paiement
    template_name = 'sales/commercial_payment_validation_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        # 🔧 FIX: Afficher SEULEMENT les paiements en attente (enregistre)
        # Les validés doivent disparaître de cette vue
        queryset = Paiement.objects.filter(
            statut=PaiementStatus.ENREGISTRE  # Only pending payments, not validated
        ).select_related('reservation', 'reservation__client', 'reservation__unite').order_by('-created_at')
        
        # Filtrer par réservation si spécifié dans l'URL
        reservation_id = self.request.GET.get('reservation')
        if reservation_id:
            queryset = queryset.filter(reservation_id=reservation_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pending_count'] = self.get_queryset().count()
        
        # Ajouter info si filtré par réservation
        reservation_id = self.request.GET.get('reservation')
        if reservation_id:
            try:
                from sales.models import Reservation
                reservation = Reservation.objects.select_related('client', 'unite').get(id=reservation_id)
                ctx['filtered_reservation'] = reservation
            except Reservation.DoesNotExist:
                pass
        
        return ctx


class CommercialPaymentValidateView(RoleRequiredMixin, View):
    """ÉTAPE 8: Commercial valide un paiement (enregistré -> validé)"""
    required_roles = ["COMMERCIAL"]
    
    def post(self, request, paiement_id):
        paiement = get_object_or_404(Paiement, id=paiement_id, statut='enregistre')
        
        # Change status to validated
        paiement.statut = PaiementStatus.VALIDE
        paiement.valide_par = request.user
        paiement.save(update_fields=['statut', 'valide_par'])
        
        # 🔧 FIX: Synchroniser EcheanceLoyer si c'est une échéance loyer
        if paiement.type_paiement == PaiementType.ECHÉANCE_LOYER:
            # Mettre à jour l'échéance associée
            echeance = paiement.echeance_loyer
            if echeance:
                echeance.statut_paiement = PaiementStatus.VALIDE
                echeance.paiement = paiement  # Assurer la liaison
                echeance.save(update_fields=['statut_paiement', 'paiement'])
        
        # 🔧 FIX: Synchroniser caution si c'est une caution
        elif paiement.type_paiement == PaiementType.CAUTION:
            # Cautions: pas d'EcheanceLoyer, juste marquer comme validée
            # Quand caution est validée, générer les échéances mensuelles
            reservation = paiement.reservation
            if reservation.is_location():
                try:
                    from .utils import generer_echeances_loyer
                    from datetime import date
                    # Générer échéances depuis la date du bail
                    generer_echeances_loyer(reservation, date.today())
                except Exception as e:
                    # Log mais ne pas bloquer
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erreur création échéances: {e}")
        
        # Génération du reçu PDF (non bloquant)
        try:
            generate_payment_receipt(paiement, request.user)
        except Exception as exc:
            logger.error("Erreur lors de la génération du reçu pour le paiement %s: %s", paiement.id, exc)
        
        # Audit log
        audit_log(
            request.user,
            paiement,
            'payment_validated',
            {'previous_status': 'enregistre', 'new_status': 'valide', 'type': paiement.type_paiement},
            request
        )
        
        messages.success(
            request,
            f"✅ Paiement de {paiement.montant} FCFA validé ! "
            f"Client : {paiement.reservation.client.prenom} {paiement.reservation.client.nom}"
        )
        
        return redirect('commercial_payment_validation_list')


class PaymentReceiptDownloadView(LoginRequiredMixin, View):
    """Permet au client ou au commercial de télécharger le reçu PDF."""

    def get(self, request, paiement_id):
        paiement = get_object_or_404(Paiement, id=paiement_id)

        if not self._has_access(request.user, paiement):
            raise PermissionDenied("Vous n'avez pas accès à ce reçu.")

        if not paiement.recu_pdf:
            messages.error(request, "Aucun reçu n'est disponible pour ce paiement.")
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            redirect_name = 'commercial_dashboard' if getattr(request.user, 'is_commercial', False) or is_admin_user(request.user) else 'client_dashboard'
            return redirect(redirect_name)

        receipt_name = paiement.recu_meta.get('receipt_number') or paiement.recu_pdf.name.split('/')[-1]
        if not receipt_name.lower().endswith('.pdf'):
            receipt_name = f"{receipt_name}.pdf"

        return FileResponse(
            paiement.recu_pdf.open('rb'),
            as_attachment=True,
            filename=receipt_name,
            content_type='application/pdf'
        )

    @staticmethod
    def _has_access(user, paiement):
        if is_admin_user(user) or getattr(user, 'is_commercial', False):
            return True
        client_profile = getattr(user, 'client_profile', None)
        return bool(client_profile and paiement.reservation.client_id == client_profile.id)


# --- VUES BANQUE PARTENAIRE ---
from django.urls import reverse
from .forms_banque import BanquePartenaireForm

class BanquePartenaireCreateView(RoleRequiredMixin, CreateView):
    model = BanquePartenaire
    form_class = BanquePartenaireForm
    template_name = "sales/banque_partenaire_form.html"
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_success_url(self):
        messages.success(self.request, "Banque partenaire ajoutée avec succès.")
        return reverse("banque_partenaire_list")


class BanquePartenaireUpdateView(RoleRequiredMixin, UpdateView):
    model = BanquePartenaire
    form_class = BanquePartenaireForm
    template_name = "sales/banque_partenaire_form.html"
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_success_url(self):
        messages.success(self.request, "Banque partenaire modifiée avec succès.")
        return reverse("banque_partenaire_list")


# --- VUES GESTION DES FINANCEMENTS (COMMERCIAL/ADMIN) ---
class CommercialFinancingListView(RoleRequiredMixin, TemplateView):
    """Liste toutes les demandes de financement pour étude par le commercial"""
    template_name = "sales/commercial_financing_list.html"
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Filtrer par statut
        statut = self.request.GET.get('statut', FinancementStatus.JUSTIFICATIF_SOUMIS)
        
        if statut == 'all':
            financements = Financement.objects.select_related(
                'reservation', 'reservation__client', 'reservation__unite', 'banque'
            ).order_by('-created_at')
        else:
            financements = Financement.objects.filter(
                statut=statut
            ).select_related(
                'reservation', 'reservation__client', 'reservation__unite', 'banque'
            ).order_by('-created_at')
        
        ctx['financements'] = financements
        ctx['statut_filter'] = statut
        ctx['statuts'] = [
            (FinancementStatus.JUSTIFICATIF_SOUMIS, '📄 Justificatif soumis'),
            (FinancementStatus.ACCEPTE, '✅ Financement accepté'),
            (FinancementStatus.REFUSE, '❌ Financement rejeté'),
            ('all', 'Tous'),
        ]
        
        return ctx


class CommercialFinancingDetailView(RoleRequiredMixin, TemplateView):
    """Détail d'une demande de financement avec possibilité de changer le statut"""
    template_name = "sales/commercial_financing_detail.html"
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        financement = get_object_or_404(
            Financement,
            id=kwargs['financement_id']
        )
        
        ctx['financement'] = financement
        ctx['reservation'] = financement.reservation
        ctx['client'] = financement.reservation.client
        ctx['unite'] = financement.reservation.unite
        ctx['banque'] = financement.banque
        
        # Nouveau workflow: un seul justificatif stocké sur Financement
        ctx['justificatif'] = financement.justificatif_financement
        ctx['motif_rejet'] = financement.motif_rejet
        
        return ctx

    def post(self, request, financement_id):
        financement = get_object_or_404(Financement, id=financement_id)
        
        nouveau_statut = request.POST.get('statut')
        ancien_statut = financement.statut
        
        if nouveau_statut not in [FinancementStatus.JUSTIFICATIF_SOUMIS, FinancementStatus.ACCEPTE, FinancementStatus.REFUSE]:
            messages.error(request, "Statut invalide.")
            return redirect('commercial_financing_detail', financement_id=financement_id)

        # Vérifier que le justificatif est présent avant validation/rejet
        if nouveau_statut in [FinancementStatus.ACCEPTE, FinancementStatus.REFUSE] and not financement.justificatif_financement:
            messages.error(request, "❌ Aucun justificatif soumis. Le client doit d'abord uploader le document.")
            return redirect('commercial_financing_detail', financement_id=financement_id)

        # Motif obligatoire si rejet
        if nouveau_statut == FinancementStatus.REFUSE:
            motif = request.POST.get('motif_rejet', '').strip()
            if not motif:
                messages.error(request, "Motif de rejet obligatoire.")
                return redirect('commercial_financing_detail', financement_id=financement_id)
            financement.motif_rejet = motif
        
        financement.statut = nouveau_statut
        fields = ['statut']
        if nouveau_statut == FinancementStatus.REFUSE:
            fields.append('motif_rejet')
        else:
            # Nettoyer le motif si on valide
            financement.motif_rejet = ''
            fields.append('motif_rejet')
        financement.save(update_fields=fields)
        
        # Audit log
        audit_log(
            request.user,
            financement,
            'financing_status_change',
            {'ancien_statut': ancien_statut, 'nouveau_statut': nouveau_statut},
            request
        )
        
        # Message de succès avec emoji selon le statut
        messages_dict = {
            FinancementStatus.JUSTIFICATIF_SOUMIS: '📄 Justificatif soumis',
            FinancementStatus.ACCEPTE: '✅ Financement accepté',
            FinancementStatus.REFUSE: '❌ Financement rejeté',
        }
        
        messages.success(
            request,
            f"{messages_dict.get(nouveau_statut, 'Statut mis à jour')} - "
            f"Client : {financement.reservation.client.prenom} {financement.reservation.client.nom}"
        )
        
        return redirect('commercial_financing_detail', financement_id=financement_id)


# CLIENT FINANCING DETAIL VIEW
class ClientFinancingDetailView(RoleRequiredMixin, TemplateView):
    """Vue détail d'un financement côté client avec documents et statut"""
    template_name = 'sales/client_financing_detail.html'
    required_roles = ["CLIENT"]
    
    def get_financement(self):
        """Récupérer le financement du client"""
        try:
            client = Client.objects.get(user=self.request.user)
        except Client.DoesNotExist:
            raise Http404("Profil client non trouvé")
        
        financement = get_object_or_404(
            Financement,
            id=self.kwargs['financement_id'],
            reservation__client=client
        )
        return financement
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        financement = self.get_financement()
        
        ctx['financement'] = financement
        ctx['reservation'] = financement.reservation
        ctx['unite'] = financement.reservation.unite
        ctx['documents'] = financement.documents.all().order_by('document_type', 'numero_ordre')
        
        # Vérifier le statut des documents
        service = FinancementDocumentService()
        can_proceed, message = service.can_proceed_financing(financement)
        ctx['docs_complete'] = can_proceed
        ctx['missing_documents'] = service.get_missing_documents(financement)
        
        # Statistiques
        total_docs = 5  # brochure, cni, bulletin_salaire (1), rib, attestation
        docs_by_type = financement.documents.values('document_type').distinct().count()
        validated_docs = financement.documents.filter(statut='valide').count()
        rejected_docs = financement.documents.filter(statut='rejete').count()
        
        ctx['total_docs_uploaded'] = financement.documents.count()
        ctx['validated_docs'] = validated_docs
        ctx['rejected_docs'] = rejected_docs
        ctx['pending_docs'] = financement.documents.filter(statut='en_attente').count()
        
        return ctx


class BanquePartenaireListView(RoleRequiredMixin, TemplateView):
    template_name = "sales/banque_partenaire_list.html"
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["banques"] = BanquePartenaire.objects.all().order_by("nom")
        return ctx


# ============================
#   CONTRAT OTP VIEWS
# ============================

class CommercialGenerateOTPView(RoleRequiredMixin, View):
    """Vue pour générer un OTP de signature de contrat (Commercial)"""
    required_roles = ["COMMERCIAL"]
    
    def post(self, request, *args, **kwargs):
        """Générer OTP et rediriger"""
        from sales.services.signature_service import SignatureService
        from core.utils import audit_log
        from django.utils import timezone
        
        try:
            contrat = get_object_or_404(Contrat, id=kwargs['contrat_id'])
            reservation = contrat.reservation
            
            # Vérifications
            if contrat.statut != 'brouillon':
                messages.error(request, "❌ Contrat doit être en état brouillon")
                return redirect('commercial_reservation_detail', reservation_id=reservation.id)
            
            if contrat.signe_le:
                messages.error(request, "❌ Contrat déjà signé")
                return redirect('commercial_reservation_detail', reservation_id=reservation.id)
            
            if SignatureService.is_contrat_blocked(contrat):
                messages.error(request, "❌ Trop de tentatives de signature. Réessayez dans 15 minutes")
                return redirect('commercial_reservation_detail', reservation_id=reservation.id)
            
            # Générer OTP
            otp = SignatureService.generate_otp(contrat)
            
            # Mettre à jour otp_generated_at
            contrat.otp_generated_at = timezone.now()
            contrat.save()
            
            # Audit log
            audit_log(request.user, contrat, 'otp_generated', {
                'otp': otp,
                'generated_at': str(timezone.now())
            }, request)
            
            messages.success(request, f"✅ OTP généré: {otp} (valide 5 minutes)")
            
        except Contrat.DoesNotExist:
            messages.error(request, "❌ Contrat non trouvé")
        except Exception as e:
            messages.error(request, f"❌ Erreur: {str(e)}")
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)


class ClientSignContratView(RoleRequiredMixin, View):
    """Vue pour que le client signe le contrat avec OTP"""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_sign_contrat.html'
    
    def get_contrat_and_reservation(self, contrat_id, reservation_id):
        """Helper pour récupérer contrat et vérifier ownership"""
        try:
            client = Client.objects.get(user=self.request.user)
        except Client.DoesNotExist:
            raise Http404("Profil client non trouvé")
        
        contrat = get_object_or_404(Contrat, id=contrat_id)
        reservation = get_object_or_404(Reservation, id=reservation_id, client=client)
        
        if contrat != reservation.contrat:
            raise Http404("Contrat ne correspond pas à la réservation")
        
        return contrat, reservation, client
    
    def get(self, request, *args, **kwargs):
        """Afficher le formulaire OTP"""
        from sales.services.signature_service import SignatureService
        from .forms import SignContratOTPForm
        
        try:
            contrat, reservation, client = self.get_contrat_and_reservation(
                kwargs['contrat_id'],
                kwargs['reservation_id']
            )
            
            # Vérifications
            if contrat.statut != 'brouillon':
                messages.error(request, "❌ Contrat déjà signé")
                return redirect('client_reservation_detail', reservation_id=reservation.id)
            
            # Vérifier si OTP est disponible
            if not SignatureService.otp_exists(contrat):
                messages.warning(request, "⏳ En attente de génération de l'OTP par le commercial")
            
            ctx = {
                'contrat': contrat,
                'reservation': reservation,
                'client': client,
                'form': SignContratOTPForm(),
                'otp_remaining_seconds': SignatureService.get_otp_remaining_time(contrat) or 0,
                'is_blocked': SignatureService.is_contrat_blocked(contrat),
            }
            
            return render(request, self.template_name, ctx)
            
        except Http404:
            raise
        except Exception as e:
            messages.error(request, f"❌ Erreur: {str(e)}")
            return redirect('client_reservation_detail', reservation_id=kwargs.get('reservation_id', ''))
    
    def post(self, request, *args, **kwargs):
        """Traiter la signature OTP"""
        from sales.services.signature_service import SignatureService
        from .forms import SignContratOTPForm
        from core.utils import get_client_ip
        
        try:
            contrat, reservation, client = self.get_contrat_and_reservation(
                kwargs['contrat_id'],
                kwargs['reservation_id']
            )
            
            form = SignContratOTPForm(request.POST)
            
            if not form.is_valid():
                ctx = {
                    'contrat': contrat,
                    'reservation': reservation,
                    'client': client,
                    'form': form,
                    'otp_remaining_seconds': SignatureService.get_otp_remaining_time(contrat) or 0,
                    'is_blocked': SignatureService.is_contrat_blocked(contrat),
                }
                return render(request, self.template_name, ctx)
            
            otp_provided = form.cleaned_data['otp']
            
            # Vérifier si contrat est bloqué
            if SignatureService.is_contrat_blocked(contrat):
                messages.error(request, "❌ Trop de tentatives. Contactez le commercial pour réessayer")
                return redirect('client_sign_contrat', reservation_id=reservation.id, contrat_id=contrat.id)
            
            # Vérifier l'OTP
            is_valid, message = SignatureService.verify_otp(contrat, otp_provided)
            
            if is_valid:
                # Signer le contrat
                contrat.statut = 'signe'
                contrat.signe_le = timezone.now()
                
                # Remplir otp_logs
                if not contrat.otp_logs:
                    contrat.otp_logs = {}
                
                contrat.otp_logs['signature'] = {
                    'timestamp': str(timezone.now()),
                    'ip': get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'otp_generated_at': str(contrat.otp_generated_at) if contrat.otp_generated_at else None,
                    'client_email': client.email,
                }
                
                contrat.save()
                
                # Audit log
                audit_log(request.user, contrat, 'contrat_signed', {
                    'signed_at': str(timezone.now()),
                    'client_email': client.email,
                }, request)
                
                messages.success(request, f"✅ Contrat signé avec succès le {timezone.now().strftime('%d/%m/%Y %H:%M')}")
                return redirect('client_reservation_detail', reservation_id=reservation.id)
            else:
                # OTP incorrect
                messages.error(request, f"❌ {message}")
                
                # Audit log d'échec
                audit_log(request.user, contrat, 'contrat_signature_failed', {
                    'reason': message,
                    'is_blocked': SignatureService.is_contrat_blocked(contrat),
                }, request)
                
                return redirect('client_sign_contrat', reservation_id=reservation.id, contrat_id=contrat.id)
        
        except Http404:
            raise
        except Exception as e:
            messages.error(request, f"❌ Erreur: {str(e)}")
            return redirect('client_reservation_detail', reservation_id=kwargs.get('reservation_id', ''))


# ============================
# SUIVI CHANTIER CLIENT
# ============================


class ClientSuiviChantierView(RoleRequiredMixin, ListView):
    """Vue client pour suivre l'avancement du chantier de son unité."""
    template_name = 'sales/client_suivi_chantier.html'
    context_object_name = 'avancements'
    required_roles = ["CLIENT"]
    paginate_by = 10

    def get_queryset(self):
        """Récupérer les avancements chantier de ses réservations confirmées - VENTE UNIQUEMENT."""
        from catalog.models import AvancementChantierUnite
        from core.choices import ContratStatus, OperationType
        
        client = self.request.user.client_profile
        return AvancementChantierUnite.objects.filter(
            reservation__client=client,
            reservation__contrat__statut=ContratStatus.SIGNE,
            reservation__unite__programme__type_operation=OperationType.VENTE  # 🏠 Exclure locations
        ).select_related(
            'unite', 'unite__programme', 'reservation'
        ).prefetch_related('photos').order_by('-date_pointage')

    def get_context_data(self, **kwargs):
        from core.choices import OperationType
        context = super().get_context_data(**kwargs)
        client = self.request.user.client_profile
        from core.choices import ContratStatus
        
        # Récupérer les réservations confirmées du client (VENTE UNIQUEMENT)
        context['reservations_confirmees'] = Reservation.objects.filter(
            client=client,
            contrat__statut=ContratStatus.SIGNE,
            unite__programme__type_operation=OperationType.VENTE  # 🏠 Exclure locations
        ).select_related('unite', 'unite__programme')
        
        return context


class ClientChantierDetailView(RoleRequiredMixin, TemplateView):
    """Détail complet du suivi chantier pour un client."""
    template_name = 'sales/client_chantier_detail.html'
    required_roles = ["CLIENT"]

    def get_context_data(self, **kwargs):
        from catalog.models import AvancementChantierUnite, MessageChantier
        from core.choices import ContratStatus, OperationType
        
        context = super().get_context_data(**kwargs)
        client = self.request.user.client_profile
        
        try:
            # Vérifier que c'est bien son avancement (VENTE UNIQUEMENT)
            avancement = AvancementChantierUnite.objects.get(
                pk=self.kwargs['pk'],
                reservation__client=client,
                reservation__contrat__statut=ContratStatus.SIGNE,
                reservation__unite__programme__type_operation=OperationType.VENTE  # 🏠 Exclure locations
            )
            context['avancement'] = avancement
            context['photos'] = avancement.photos.all().order_by('-pris_le')
            
            # Historique des 10 derniers avancements
            context['historique'] = avancement.unite.avancements_chantier.exclude(
                pk=avancement.pk
            ).order_by('-date_pointage')[:10]
            
            # Tous les avancements de cette unité pour le client (VENTE UNIQUEMENT)
            context['tous_avancements'] = avancement.unite.avancements_chantier.filter(
                reservation__client=client,
                reservation__unite__programme__type_operation=OperationType.VENTE
            ).order_by('-date_pointage')
            
            # Messages entre client et commercial (exclure les messages supprimés pour cet utilisateur)
            # Utiliser exclude au lieu de filter Python pour plus de fiabilité
            context['messages'] = avancement.messages.exclude(supprime_par=self.request.user).order_by('created_at')
            
            # Informations du commercial
            if avancement.unite.programme.contact_commercial:
                context['commercial'] = avancement.unite.programme.contact_commercial
                # Téléphone du commercial (si existe)
                if hasattr(context['commercial'], 'telephone'):
                    context['commercial_telephone'] = context['commercial'].telephone
                else:
                    context['commercial_telephone'] = None
            else:
                context['commercial'] = None
                context['commercial_telephone'] = None
            
        except AvancementChantierUnite.DoesNotExist:
            raise Http404("Avancement non trouvé")
        
        return context

# ============================================================================
# MESSAGES CHANTIER - Client <-> Commercial
# ============================================================================

@method_decorator(login_required(login_url='login'), name='dispatch')
class ClientSendMessageChantierView(RoleRequiredMixin, View):
    """Permet au client d'envoyer un message au commercial sur un avancement."""
    required_roles = ["CLIENT"]
    
    def post(self, request, avancement_id):
        from catalog.models import AvancementChantierUnite, MessageChantier
        
        client = get_object_or_404(Client, user=request.user)
        avancement = get_object_or_404(AvancementChantierUnite, id=avancement_id)
        
        # Vérifier que l'avancement appartient bien au client (via sa réservation)
        if not avancement.reservation or avancement.reservation.client != client:
            messages.error(request, "Vous n'avez pas accès à cet avancement.")
            return redirect('client_suivi_chantier')
        
        message_text = request.POST.get('message', '').strip()
        if not message_text:
            messages.error(request, "Le message ne peut pas être vide.")
            return redirect('client_chantier_detail', pk=avancement_id)
        
        # Créer le message
        MessageChantier.objects.create(
            avancement=avancement,
            auteur=request.user,
            message=message_text,
            lu=False
        )
        
        messages.success(request, "✅ Votre message a été envoyé au commercial.")
        return redirect('client_chantier_detail', pk=avancement_id)


# ============================
#   MESSAGING SYSTEM - CHAT
# ============================

class CommercialReplyMessageChantierView(RoleRequiredMixin, View):
    """Commercial répond aux messages des clients (DEPRECATED - utiliser CommercialSendMessageChantierView)"""
    required_roles = ["COMMERCIAL", "ADMIN"]

    def post(self, request, message_id):
        # Récupérer le message
        msg = get_object_or_404(MessageChantier, id=message_id)
        avancement = msg.avancement

        # Vérifier que c'est bien le commercial du programme
        if request.user != avancement.unite.programme.contact_commercial and not is_admin_user(request.user):
            raise Http404("Vous n'êtes pas autorisé à répondre à ce message.")

        # Récupérer la réponse
        reponse = request.POST.get('reponse', '').strip()
        if reponse:
            msg.reponse = reponse
            msg.repondu_par = request.user
            msg.lu = True  # Marquer comme lu
            msg.save()
            messages.success(request, "✅ Votre réponse a été envoyée.")

        return redirect('avancement_detail', pk=avancement.id)


class CommercialSendMessageChantierView(RoleRequiredMixin, View):
    """Commercial envoie un message/réponse aux clients (nouveau message ou réponse)"""
    required_roles = ["COMMERCIAL", "ADMIN"]

    def post(self, request, avancement_id):
        avancement = get_object_or_404(AvancementChantierUnite, id=avancement_id)

        # Vérifier que c'est bien le commercial du programme
        if request.user != avancement.unite.programme.contact_commercial and not is_admin_user(request.user):
            raise Http404("Vous n'êtes pas autorisé à envoyer des messages sur cet avancement.")

        # Récupérer le message
        message_text = request.POST.get('message', '').strip()
        if message_text:
            # Créer un nouveau message de type "réponse"
            MessageChantier.objects.create(
                avancement=avancement,
                auteur=request.user,
                message=message_text,
                lu=True  # Les messages du commercial sont marqués comme lus
            )
            messages.success(request, "✅ Votre message a été envoyé.")

        return redirect('avancement_detail', pk=avancement_id)


class DeleteMessageChantierView(RoleRequiredMixin, View):
    """Supprimer un message (soft delete - disparaît seulement pour celui qui le supprime)"""
    required_roles = ["CLIENT", "COMMERCIAL", "ADMIN"]

    def post(self, request, message_id):
        msg = get_object_or_404(MessageChantier, id=message_id)
        avancement = msg.avancement

        # Vérifier les permissions
        is_admin = is_admin_user(request.user)
        is_client = request.user.roles.filter(code="CLIENT").exists()
        is_commercial = request.user.roles.filter(code="COMMERCIAL").exists()
        
        redirect_url = None
        
        # Admin peut toujours supprimer
        if is_admin:
            redirect_url = 'avancement_detail'
        # Commercial peut supprimer les messages de ses programmes (priorité sur CLIENT)
        elif is_commercial:
            # Vérifier que c'est le bon commercial pour ce programme
            if request.user != avancement.unite.programme.contact_commercial:
                raise Http404("Vous n'êtes pas autorisé à accéder à ce message.")
            redirect_url = 'avancement_detail'
        # Client peut supprimer ses propres messages
        elif is_client:
            try:
                client_profile = request.user.client_profile
                reservation = avancement.reservation
                if not reservation or reservation.client != client_profile:
                    raise Http404("Vous n'êtes pas autorisé à accéder à ce message.")
            except AttributeError:
                raise Http404("Vous n'êtes pas autorisé à accéder à ce message.")
            redirect_url = 'client_chantier_detail'
        else:
            raise Http404("Vous n'êtes pas autorisé à accéder à ce message.")

        # Soft delete - Ajouter l'utilisateur à la liste des utilisateurs qui ont supprimé
        msg.supprime_par.add(request.user)
        messages.success(request, "✅ Message supprimé de votre vue.")

        # Redirection
        return redirect(redirect_url, pk=avancement.id)


class ClearChatChantierView(RoleRequiredMixin, View):
    """Vider tous les messages d'un avancement (commercial ou client) - Soft delete"""
    required_roles = ["CLIENT", "COMMERCIAL", "ADMIN"]

    def post(self, request, avancement_id):
        avancement = get_object_or_404(AvancementChantierUnite, id=avancement_id)

        # Vérifier les permissions
        is_admin = is_admin_user(request.user)
        is_client = request.user.roles.filter(code="CLIENT").exists()
        is_commercial = request.user.roles.filter(code="COMMERCIAL").exists()
        
        redirect_url = None
        
        # Admin peut toujours vider
        if is_admin:
            redirect_url = 'avancement_detail'
        # Commercial peut vider les messages de ses programmes (priorité sur CLIENT)
        elif is_commercial:
            # Vérifier que c'est le bon commercial pour ce programme
            if request.user != avancement.unite.programme.contact_commercial:
                raise Http404("Vous n'êtes pas autorisé à vider ce chat.")
            redirect_url = 'avancement_detail'
        # Client peut vider ses propres messages
        elif is_client:
            try:
                client_profile = request.user.client_profile
                reservation = avancement.reservation
                if not reservation or reservation.client != client_profile:
                    raise Http404("Vous n'êtes pas autorisé à vider ce chat.")
            except AttributeError:
                raise Http404("Vous n'êtes pas autorisé à vider ce chat.")
            redirect_url = 'client_chantier_detail'
        else:
            raise Http404("Vous n'êtes pas autorisé à vider ce chat.")

        # Soft delete - Ajouter l'utilisateur à tous les messages
        for msg in avancement.messages.all():
            msg.supprime_par.add(request.user)
        
        messages.success(request, "✅ Chat vidé. Tous les messages sont supprimés de votre vue.")
        return redirect(redirect_url, pk=avancement_id)
