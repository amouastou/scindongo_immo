from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib import messages
from django.http import Http404

from accounts.mixins import RoleRequiredMixin
from accounts.models import User, Role
from catalog.models import Unite
from .models import Client, Reservation, ReservationDocument, FinancementDocument, Paiement, Contrat, Financement, BanquePartenaire
from .forms import ReservationForm, ReservationDocumentForm, FinancementDocumentForm, PaiementForm, ClientForm, FinancementForm, ContratForm, PaymentModeForm, FinancingRequestForm
from .utils import set_pending_unite
from .document_services import ReservationDocumentService
from .financing_document_service import FinancementDocumentService
from .mixins import ReservationRequiredMixin, FinancementFormMixin, ContratFormMixin, PaiementFormMixin
from core.utils import audit_log

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum

from catalog.models import Programme, Unite
from sales.models import Reservation, Paiement, Financement, BanquePartenaire


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

    def get_document(self):
        """Récupérer le document"""
        doc = get_object_or_404(ReservationDocument, id=self.kwargs['document_id'])
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

    def get_document(self):
        """Récupérer le document"""
        doc = get_object_or_404(ReservationDocument, id=self.kwargs['document_id'])
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
            # Supprimer l'ancien fichier avant de sauvegarder le nouveau
            old_file = doc.fichier
            if old_file:
                old_file.delete(save=False)
            
            # Sauvegarder le formulaire (qui va uploader le nouveau fichier)
            updated_doc = form.save(commit=False)
            updated_doc.statut = 'en_attente'  # Réinitialiser statut
            updated_doc.raison_rejet = ''
            updated_doc.verifie_par = None
            updated_doc.verifie_le = None
            updated_doc.save()
            
            messages.success(request, f"✅ Document '{updated_doc.get_document_type_display()}' mis à jour avec succès!")
            
            # Log audit
            audit_log(request.user, updated_doc, 'financing_document_updated',
                     {'document_type': updated_doc.document_type}, request)
            
            # Rediriger vers page financements du client
            return redirect('financing_documents_upload', financement_id=updated_doc.financement.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        return render(request, self.template_name, self.get_context_data())


class CommercialFinancingDocumentRejectView(RoleRequiredMixin, TemplateView):
    """Vue pour que le Commercial rejette un document de financement"""
    template_name = 'sales/commercial_financing_document_reject.html'
    required_roles = ["COMMERCIAL"]

    def get_document(self):
        """Récupérer le document"""
        doc = get_object_or_404(FinancementDocument, id=self.kwargs['document_id'])
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

    def get_document(self):
        """Récupérer le document"""
        doc = get_object_or_404(FinancementDocument, id=self.kwargs['document_id'])
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
        from .models import Contrat, Financement
        ctx = super().get_context_data(**kwargs)
        client = getattr(self.request.user, "client_profile", None)
        if client:
            ctx["reservations"] = client.reservations.select_related("unite", "unite__programme")
            ctx["paiements"] = Paiement.objects.filter(reservation__client=client)
            ctx["contrats"] = Contrat.objects.filter(reservation__client=client)
            ctx["financements"] = Financement.objects.filter(reservation__client=client)
        else:
            ctx["reservations"] = []
            ctx["paiements"] = []
            ctx["contrats"] = []
            ctx["financements"] = []
        return ctx


class CommercialDashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboards/commercial_dashboard.html'
    required_roles = ["COMMERCIAL"]

    def get_context_data(self, **kwargs):
        from .models import Reservation, Paiement, Financement, Contrat
        from catalog.models import Programme
        from accounts.models import User, Role
        
        ctx = super().get_context_data(**kwargs)
        
        # Comptes
        ctx["clients_count"] = Client.objects.count()
        ctx["reservations_count"] = Reservation.objects.count()
        ctx["paiements_count"] = Paiement.objects.count()
        ctx["financements_count"] = Financement.objects.count()
        
        # ÉTAPE 3: Réservations en attente (en_cours) en priorité
        ctx["pending_reservations"] = Reservation.objects.filter(
            statut="en_cours"
        ).select_related("client", "unite", "unite__programme").order_by('-created_at')
        ctx["pending_count"] = ctx["pending_reservations"].count()
        
        # ÉTAPE 8: Paiements en attente de validation
        ctx["pending_payments"] = Paiement.objects.filter(
            statut="enregistre"
        ).select_related("reservation", "reservation__client", "reservation__unite").order_by('-created_at')
        ctx["pending_payments_count"] = ctx["pending_payments"].count()
        
        # Listes détaillées
        ctx["reservations"] = Reservation.objects.select_related("client", "unite", "unite__programme").all()[:20]
        ctx["clients"] = Client.objects.select_related("user").all()[:20]
        ctx["paiements"] = Paiement.objects.select_related("reservation", "reservation__client").all()[:20]
        ctx["financements"] = Financement.objects.select_related("banque", "reservation", "reservation__client").all()[:20]
        ctx["programmes"] = Programme.objects.filter(statut="actif").all()
        
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
        ctx["financements_acceptes"] = Financement.objects.filter(statut="accepte").count()
        ctx["financements_en_etude"] = Financement.objects.filter(statut="en_etude").count()
        
        # Contrats et banques
        ctx["contrats_count"] = Contrat.objects.count()
        ctx["contrats_signes"] = Contrat.objects.filter(statut="signe").count()
        ctx["banques_count"] = BanquePartenaire.objects.count()
        
        # Listes détaillées
        ctx["programmes"] = Programme.objects.all().order_by("-created_at")[:10]
        ctx["derniers_paiements"] = Paiement.objects.select_related("reservation", "reservation__client").order_by("-date_paiement")[:10]
        ctx["dernieres_reservations"] = Reservation.objects.select_related("client", "unite", "unite__programme").order_by("-created_at")[:10]
        
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
        
        # Documents
        ctx['documents'] = reservation.documents.all()
        documents_valides = reservation.documents.filter(statut='valide').count()
        documents_rejetes = reservation.documents.filter(statut='rejete').count()
        ctx['documents_valides'] = documents_valides == 3  # Tous 3 docs valides
        ctx['documents_rejetes'] = documents_rejetes > 0
        ctx['missing_documents'] = ReservationDocumentService.get_missing_documents(reservation)
        
        return ctx


class DashboardAdminView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "sales/admin_dashboard.html"

    def test_func(self):
        """
        Autoriser :
        - admin scindongo
        - superuser
        - staff Django
        """
        u = self.request.user
        return bool(
            u
            and u.is_authenticated
            and (
                getattr(u, "is_admin_scindongo", False)
                or u.is_superuser
                or u.is_staff
            )
        )

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

class CommercialReservationConfirmView(RoleRequiredMixin, TemplateView):
    """
    Vue pour que le commercial CONFIRME une réservation (en_cours → confirmée)
    Avant confirmation, vérifier la KYC du client
    """
    template_name = 'sales/commercial_reservation_confirm.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        ctx['reservation'] = reservation
        ctx['client'] = reservation.client
        ctx['unite'] = reservation.unite
        
        return ctx
    
    def post(self, request, reservation_id):
        """Valider la réservation"""
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
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
    """Liste des clients pour le commercial"""
    model = Client
    template_name = 'sales/commercial_client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    required_roles = ["COMMERCIAL"]
    
    def get_queryset(self):
        return Client.objects.select_related('user').order_by('-created_at')


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
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Client {self.object.nom} mis à jour")
        audit_log(self.request.user, self.object, "client_update", {"nom": self.object.nom}, self.request)
        return response


class CommercialReservationListView(RoleRequiredMixin, ListView):
    """Liste des réservations pour le commercial"""
    model = Reservation
    template_name = 'sales/commercial_reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    required_roles = ["COMMERCIAL"]
    
    def get_queryset(self):
        return Reservation.objects.select_related('client', 'unite', 'unite__programme').order_by('-created_at')


class CommercialReservationDetailView(RoleRequiredMixin, TemplateView):
    """Détail d'une réservation avec actions possibles + documents + messages"""
    template_name = 'sales/commercial_reservation_detail.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
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
        
        return ctx
    
    def post(self, request, *args, **kwargs):
        """Traiter les actions (validation doc, message, etc)"""
        action = request.POST.get('action')
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        
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


class CommercialFinancementCreateView(RoleRequiredMixin, CreateView):
    """Créer un financement pour une réservation"""
    model = Financement
    form_class = FinancementForm
    template_name = 'sales/commercial_financement_form.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        ctx['reservation'] = reservation
        return ctx
    
    def form_valid(self, form):
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        
        # Vérifier qu'il n'y a pas déjà un financement
        if hasattr(reservation, 'financement'):
            messages.error(self.request, "Un financement existe déjà pour cette réservation")
            return self.form_invalid(form)
        
        financement = form.save(commit=False)
        financement.reservation = reservation
        financement.statut = "soumis"
        financement.save()
        
        messages.success(self.request, "Financement créé et soumis à la banque")
        audit_log(self.request.user, financement, "financement_create", 
                 {"banque": financement.banque.nom, "montant": str(financement.montant)}, self.request)
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        # Pré-remplir le montant avec le prix de l'unité
        kwargs['initial'] = {'montant': reservation.unite.prix_ttc}
        return kwargs


class CommercialFinancementUpdateView(RoleRequiredMixin, UpdateView):
    """Mettre à jour le statut d'un financement"""
    model = Financement
    fields = ['statut']
    template_name = 'sales/commercial_financement_update.html'
    required_roles = ["COMMERCIAL"]
    
    def get_object(self):
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        return get_object_or_404(Financement, reservation=reservation)
    
    def get_success_url(self):
        return reverse_lazy('commercial_reservation_detail', kwargs={'reservation_id': self.object.reservation.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Financement mis à jour: {self.object.get_statut_display()}")
        audit_log(self.request.user, self.object, "financement_update", 
                 {"statut": self.object.statut}, self.request)
        return response


class CommercialContratCreateView(RoleRequiredMixin, CreateView):
    """Créer un contrat pour une réservation"""
    model = Contrat
    form_class = ContratForm
    template_name = 'sales/commercial_contrat_form.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        ctx['reservation'] = reservation
        return ctx
    
    def form_valid(self, form):
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        
        # Vérifier qu'il n'y a pas déjà un contrat
        if hasattr(reservation, 'contrat'):
            messages.error(self.request, "Un contrat existe déjà pour cette réservation")
            return self.form_invalid(form)
        
        contrat = form.save(commit=False)
        contrat.reservation = reservation
        contrat.numero = f"CTR-{reservation.id}-{reservation.created_at.strftime('%Y%m%d')}"
        contrat.statut = "brouillon"
        contrat.save()
        
        messages.success(self.request, f"Contrat {contrat.numero} créé. À signer via OTP")
        audit_log(self.request.user, contrat, "contrat_create", 
                 {"numero": contrat.numero}, self.request)
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)


class CommercialContratUpdateView(RoleRequiredMixin, UpdateView):
    """Mettre à jour le statut d'un contrat"""
    model = Contrat
    fields = ['statut']
    template_name = 'sales/commercial_contrat_update.html'
    required_roles = ["COMMERCIAL"]
    
    def get_object(self):
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        return get_object_or_404(Contrat, reservation=reservation)
    
    def get_success_url(self):
        return reverse_lazy('commercial_reservation_detail', kwargs={'reservation_id': self.object.reservation.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Contrat mis à jour: {self.object.get_statut_display()}")
        audit_log(self.request.user, self.object, "contrat_update", 
                 {"statut": self.object.statut}, self.request)
        return response


class CommercialPaiementCreateView(RoleRequiredMixin, CreateView):
    """Créer un paiement pour une réservation"""
    model = Paiement
    form_class = PaiementForm
    template_name = 'sales/commercial_paiement_form.html'
    required_roles = ["COMMERCIAL"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        ctx['reservation'] = reservation
        return ctx
    
    def form_valid(self, form):
        reservation = get_object_or_404(Reservation, id=self.kwargs.get('reservation_id'))
        
        paiement = form.save(commit=False)
        paiement.reservation = reservation
        paiement.statut = "valide"  # Le commercial valide directement
        paiement.save()
        
        messages.success(self.request, f"Paiement de {paiement.montant} enregistré et validé")
        audit_log(self.request.user, paiement, "paiement_create", 
                 {"montant": str(paiement.montant), "moyen": paiement.moyen}, self.request)
        
        return redirect('commercial_reservation_detail', reservation_id=reservation.id)


# ÉTAPE 5: Client choose payment mode (Direct vs Financing)
class ClientPaymentModeChoiceView(RoleRequiredMixin, TemplateView):
    """ÉTAPE 5: Client choisit le mode de paiement après confirmation"""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_payment_mode_choice.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reservation_id = self.kwargs.get('reservation_id')
        
        # Chercher le Client de l'utilisateur actuel
        try:
            client = Client.objects.get(user=self.request.user)
        except Client.DoesNotExist:
            raise Http404(f"Pas de profil Client trouvé pour l'utilisateur {self.request.user.email}")
        
        # Chercher la réservation (sans imposer le statut 'confirmee')
        try:
            reservation = Reservation.objects.get(id=reservation_id, client=client)
        except Reservation.DoesNotExist:
            raise Http404(f"Réservation {reservation_id} introuvable pour le client {client.id}")
        
        ctx['reservation'] = reservation
        ctx['unite'] = reservation.unite
        ctx['remaining_amount'] = reservation.unite.prix_ttc - reservation.acompte
        ctx['form'] = PaymentModeForm()
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
        
        
        form = PaymentModeForm(request.POST)
        if not form.is_valid():
            return self.get(request, reservation_id=reservation_id)
        
        payment_mode = form.cleaned_data['payment_mode']
        
        if payment_mode == 'direct':
            # Redirect to direct payment
            return redirect('client_direct_payment', reservation_id=reservation_id)
        else:  # financing
            # Redirect to financing request
            return redirect('client_financing_request', reservation_id=reservation_id)


# ÉTAPE 6: Direct Payment View
class ClientDirectPaymentView(RoleRequiredMixin, TemplateView):
    """ÉTAPE 6: Client fait un paiement direct (virement, chèque, espèces, carte)"""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_direct_payment.html'
    
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
    """ÉTAPE 7: Client demande un financement bancaire"""
    required_roles = ["CLIENT"]
    template_name = 'sales/client_financing_request.html'
    
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
        
        form = FinancingRequestForm(request.POST)
        if not form.is_valid():
            context = self.get_context_data(reservation_id=reservation_id)
            context['form'] = form
            return self.render_to_response(context)
        
        financement = form.save(commit=False)
        financement.reservation = reservation
        financement.statut = 'soumis'  # Initial status
        
        # Validation: montant ne peut pas dépasser le montant restant
        prix_total = reservation.unite.prix_ttc
        acompte = reservation.acompte or 0
        
        # Soustraire les paiements validés déjà effectués
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
            'financing_request',
            {
                'montant': str(financement.montant),
                'banque': str(financement.banque),
                'statut': 'soumis'
            },
            request
        )
        
        messages.success(
            request,
            f"✅ Demande de financement de {financement.montant} FCFA soumise ! "
            "Veuillez maintenant uploader vos documents requis."
        )
        
        # Rediriger vers l'upload des documents de financement
        return redirect('financing_documents_upload', financement_id=financement.id)


# ÉTAPE 8: Commercial Payment Validation View
class CommercialPaymentValidationListView(RoleRequiredMixin, ListView):
    """ÉTAPE 8: Commercial valide les paiements enregistrés"""
    required_roles = ["COMMERCIAL"]
    model = Paiement
    template_name = 'sales/commercial_payment_validation_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        return Paiement.objects.filter(
            statut='enregistre'  # Only pending payments
        ).select_related('reservation', 'reservation__client', 'reservation__unite').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pending_count'] = self.get_queryset().count()
        return ctx


class CommercialPaymentValidateView(RoleRequiredMixin, View):
    """ÉTAPE 8: Commercial valide un paiement (enregistré -> validé)"""
    required_roles = ["COMMERCIAL"]
    
    def post(self, request, paiement_id):
        paiement = get_object_or_404(Paiement, id=paiement_id, statut='enregistre')
        
        # Change status to validated
        paiement.statut = 'valide'
        paiement.save(update_fields=['statut'])
        
        # Audit log
        audit_log(
            request.user,
            paiement,
            'payment_validated',
            {'previous_status': 'enregistre', 'new_status': 'valide'},
            request
        )
        
        messages.success(
            request,
            f"✅ Paiement de {paiement.montant} FCFA validé ! "
            f"Client : {paiement.reservation.client.prenom} {paiement.reservation.client.nom}"
        )
        
        return redirect('commercial_payment_validation_list')


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
        statut = self.request.GET.get('statut', 'soumis')
        
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
            ('soumis', '📮 Soumis'),
            ('en_etude', '📚 En étude'),
            ('accepte', '✅ Accepté'),
            ('refuse', '❌ Refusé'),
            ('clos', '🏁 Clos'),
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
        
        return ctx

    def post(self, request, financement_id):
        financement = get_object_or_404(Financement, id=financement_id)
        
        nouveau_statut = request.POST.get('statut')
        ancien_statut = financement.statut
        
        if nouveau_statut not in ['soumis', 'en_etude', 'accepte', 'refuse', 'clos']:
            messages.error(request, "Statut invalide.")
            return redirect('commercial_financing_detail', financement_id=financement_id)
        
        financement.statut = nouveau_statut
        financement.save(update_fields=['statut'])
        
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
            'soumis': '📮 Demande remise en attente de soumission',
            'en_etude': '📚 Demande en cours d\'étude',
            'accepte': '✅ Demande acceptée',
            'refuse': '❌ Demande refusée',
            'clos': '🏁 Dossier de financement clôturé'
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
