from django.views.generic import TemplateView, ListView, DetailView, UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from accounts.mixins import RoleRequiredMixin
from accounts.utils import is_admin_user
from .models import Programme, Unite, TypeBien, ModeleBien, AvancementChantierUnite, PhotoChantierUnite, MessageChantier
from .forms import ProgrammeForm, AvancementChantierUniteForm
from datetime import datetime


class HomeView(TemplateView):
    template_name = 'public/home.html'


class ProgrammeListView(RoleRequiredMixin, ListView):
    model = Programme
    template_name = 'catalog/programme_list.html'
    context_object_name = 'programmes'
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_queryset(self):
        user = self.request.user
        qs = Programme.objects.prefetch_related('unites').order_by("nom")

        # 🔒 ADMIN voit tout, COMMERCIAL seulement ses programmes
        if is_admin_user(user):
            return qs

        return qs.filter(contact_commercial=user)


class ProgrammeDetailView(RoleRequiredMixin, DetailView):
    model = Programme
    template_name = 'catalog/programme_detail.html'
    context_object_name = 'programme'
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_queryset(self):
        user = self.request.user
        qs = Programme.objects.prefetch_related('unites', 'unites__reservations')
        
        # 🔒 ADMIN voit tout, COMMERCIAL seulement ses programmes
        if is_admin_user(user):
            return qs
        
        return qs.filter(contact_commercial=user)


class UniteDetailView(RoleRequiredMixin, DetailView):
    model = Unite
    template_name = 'catalog/unite_detail.html'
    context_object_name = 'unite'
    required_roles = ["ADMIN", "COMMERCIAL"]

    def get_queryset(self):
        user = self.request.user
        qs = Unite.objects.select_related(
            'programme', 'modele_bien', 'modele_bien__type_bien'
        ).prefetch_related('reservations')

        if is_admin_user(user):
            return qs

        return qs.filter(programme__contact_commercial=user)


class BiensListView(ListView):
    """
    Page publique pour afficher tous les biens disponibles avec filtrage
    """
    model = Unite
    template_name = 'catalog/biens_list.html'
    context_object_name = 'biens'
    paginate_by = 12

    def get_queryset(self):
        queryset = Unite.objects.select_related('programme', 'modele_bien', 'modele_bien__type_bien')
        
        # Filtrage par recherche
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(reference_lot__icontains=search) |
                Q(programme__nom__icontains=search)
            )
        
        # Filtrage par programme
        programme_id = self.request.GET.get('programme', '')
        if programme_id:
            queryset = queryset.filter(programme_id=programme_id)
        
        # Filtrage par statut
        statut = self.request.GET.get('statut', '')
        if statut:
            queryset = queryset.filter(statut_disponibilite=statut)
        
        return queryset.order_by('programme', 'reference_lot')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programmes'] = Programme.objects.all().order_by('nom')
        
        # Statistiques globales - optimisées avec raw SQL pour performance
        from django.db import connection
        
        cursor = connection.cursor()
        
        # Une seule requête SQL pour tout
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT u.id) as total,
                COUNT(DISTINCT CASE WHEN r.statut = 'confirmee' THEN u.id END) as vendus,
                COUNT(DISTINCT CASE WHEN r.statut IN ('en_cours', 'reserve') AND r.statut != 'annulee' THEN u.id END) as reserves
            FROM catalog_unite u
            LEFT JOIN sales_reservation r ON u.id = r.unite_id
        """)
        
        row = cursor.fetchone()
        context['total_biens'] = row[0] if row[0] else 0
        context['biens_vendus'] = row[1] if row[1] else 0
        context['biens_reserves'] = row[2] if row[2] else 0
        context['biens_disponibles'] = context['total_biens'] - context['biens_vendus'] - context['biens_reserves']
        
        return context

# === Pages publiques supplémentaires ===

class PourquoiInvestirView(TemplateView):
    """
    Page marketing expliquant pourquoi investir avec SCINDONGO Immo
    (conforme à l'esprit du document de cadrage).
    """
    template_name = 'public/pourquoi_investir.html'


class PublicProgrammeListView(ListView):
    """
    Page publique affichant les programmes disponibles (vente et location).
    Accessible à tous les utilisateurs (authentifiés ou non).
    """
    model = Programme
    template_name = 'catalog/programme_list.html'
    context_object_name = 'programmes'
    paginate_by = 12

    def get_queryset(self):
        """Afficher seulement les programmes actifs au public"""
        return Programme.objects.filter(
            statut='actif'
        ).prefetch_related('unites').order_by("nom")


class PublicProgrammeDetailView(DetailView):
    """
    Page de détail publique d'un programme.
    Accessible à tous les utilisateurs (authentifiés ou non).
    """
    model = Programme
    template_name = 'catalog/programme_detail.html'
    context_object_name = 'programme'

    def get_queryset(self):
        """Afficher seulement les programmes actifs au public"""
        return Programme.objects.filter(
            statut='actif'
        ).prefetch_related('unites', 'unites__reservations')


class ContactView(TemplateView):
    """
    Page de contact : coordonnées, formulaire de prise de contact simple.
    (on peut plus tard brancher un envoi d'email ou un modèle ContactMessage).
    """
    template_name = 'public/contact.html'


class ProgrammeUpdateView(RoleRequiredMixin, UpdateView):
    """
    Vue pour modifier un programme (accessible aux ADMIN et COMMERCIAL)
    """
    model = Programme
    template_name = 'catalog/programme_form.html'
    form_class = ProgrammeForm
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('programme_list')

    def get_queryset(self):
        user = self.request.user
        qs = Programme.objects.all()

        if is_admin_user(user):
            return qs

        return qs.filter(contact_commercial=user)

    def form_valid(self, form):
        user = self.request.user
        if not is_admin_user(user):
            form.instance.contact_commercial = user
        return super().form_valid(form)


class ProgrammeCreateView(RoleRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau programme (accessible aux ADMIN et COMMERCIAL)
    """
    model = Programme
    template_name = 'catalog/programme_form.html'
    form_class = ProgrammeForm
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('programme_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not is_admin_user(user):
            form.fields['contact_commercial'].queryset = form.fields['contact_commercial'].queryset.filter(pk=user.pk)
            form.fields['contact_commercial'].initial = user
        return form

    def form_valid(self, form):
        user = self.request.user
        if not is_admin_user(user):
            form.instance.contact_commercial = user
        return super().form_valid(form)


class ProgrammeDeleteView(RoleRequiredMixin, DeleteView):
    """
    Vue pour supprimer un programme (accessible aux ADMIN uniquement)
    """
    model = Programme
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('programme_list')
    
    def post(self, request, *args, **kwargs):
        """Suppression directe sans page de confirmation"""
        return self.delete(request, *args, **kwargs)


# === Gestion des Types de biens ===

class TypeBienListView(RoleRequiredMixin, ListView):
    """Liste des types de biens (ADMIN/COMMERCIAL)"""
    model = TypeBien
    template_name = 'catalog/typebien_list.html'
    context_object_name = 'types'
    required_roles = ["ADMIN", "COMMERCIAL"]
    paginate_by = 20


class TypeBienCreateView(RoleRequiredMixin, CreateView):
    """Créer un type de bien (ADMIN/COMMERCIAL)"""
    model = TypeBien
    template_name = 'catalog/typebien_form.html'
    fields = ['code', 'libelle']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('typebien_list')


class TypeBienUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier un type de bien (ADMIN/COMMERCIAL)"""
    model = TypeBien
    template_name = 'catalog/typebien_form.html'
    fields = ['code', 'libelle']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('typebien_list')


class TypeBienDeleteView(RoleRequiredMixin, DeleteView):
    """Supprimer un type de bien (ADMIN uniquement)"""
    model = TypeBien
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('typebien_list')
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# === Gestion des Modèles de biens ===

class ModeleBienListView(RoleRequiredMixin, ListView):
    """Liste des modèles de biens (ADMIN/COMMERCIAL)"""
    model = ModeleBien
    template_name = 'catalog/modelebien_list.html'
    context_object_name = 'modeles'
    required_roles = ["ADMIN", "COMMERCIAL"]
    paginate_by = 20


class ModeleBienCreateView(RoleRequiredMixin, CreateView):
    """Créer un modèle de bien (ADMIN/COMMERCIAL)"""
    model = ModeleBien
    template_name = 'catalog/modelebien_form.html'
    fields = ['type_bien', 'nom_marketing', 'surface_hab_m2', 'prix_base_ttc', 'description']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('modelebien_list')


class ModeleBienUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier un modèle de bien (ADMIN/COMMERCIAL)"""
    model = ModeleBien
    template_name = 'catalog/modelebien_form.html'
    fields = ['type_bien', 'nom_marketing', 'surface_hab_m2', 'prix_base_ttc', 'description']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('modelebien_list')


class ModeleBienDeleteView(RoleRequiredMixin, DeleteView):
    """Supprimer un modèle de bien (ADMIN uniquement)"""
    model = ModeleBien
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('modelebien_list')
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


# === Gestion des Unités ===

class UniteListView(RoleRequiredMixin, ListView):
    """Liste des unités (filtrée par commercial)"""
    model = Unite
    template_name = 'catalog/unite_list.html'
    context_object_name = 'unites'
    required_roles = ["ADMIN", "COMMERCIAL"]
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        qs = Unite.objects.select_related('programme', 'modele_bien', 'modele_bien__type_bien')
        
        # 🔒 ADMIN voit toutes les unités, COMMERCIAL seulement les siennes
        if is_admin_user(user):
            return qs.all()
        
        # Seulement les unités de MES programmes
        return qs.filter(programme__contact_commercial=user)


class UniteCreateView(RoleRequiredMixin, CreateView):
    """Créer une unité (ADMIN/COMMERCIAL)"""
    model = Unite
    template_name = 'catalog/unite_form.html'
    fields = ['programme', 'modele_bien', 'reference_lot', 'prix_ttc', 'statut_disponibilite', 'gps_lat', 'gps_lng', 'image']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('unite_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not is_admin_user(user):
            form.fields['programme'].queryset = Programme.objects.filter(contact_commercial=user)
        return form

    def form_valid(self, form):
        user = self.request.user
        programme = form.cleaned_data.get('programme')
        if programme and not is_admin_user(user):
            if programme.contact_commercial != user:
                raise PermissionDenied("Vous ne pouvez créer que des unités pour vos programmes.")
        return super().form_valid(form)


class UniteUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier une unité (filtrée par commercial)"""
    model = Unite
    template_name = 'catalog/unite_form.html'
    fields = ['programme', 'modele_bien', 'reference_lot', 'prix_ttc', 'statut_disponibilite', 'gps_lat', 'gps_lng', 'image']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('unite_list')
    
    def get_queryset(self):
        user = self.request.user
        qs = Unite.objects.select_related('programme')
        
        # 🔒 ADMIN voit tout, COMMERCIAL seulement ses unités
        if is_admin_user(user):
            return qs
        
        return qs.filter(programme__contact_commercial=user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not is_admin_user(user):
            form.fields['programme'].queryset = Programme.objects.filter(contact_commercial=user)
        return form

    def form_valid(self, form):
        user = self.request.user
        programme = form.cleaned_data.get('programme')
        if programme and not is_admin_user(user):
            if programme.contact_commercial != user:
                raise PermissionDenied("Vous ne pouvez modifier que vos propres programmes.")
        return super().form_valid(form)


class UniteDeleteView(RoleRequiredMixin, DeleteView):
    """Supprimer une unité (ADMIN uniquement)"""
    model = Unite
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('unite_list')
    
    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Unité supprimée avec succès.")
        return self.delete(request, *args, **kwargs)


# ============================
# GESTION CHANTIER PAR UNITÉ
# ============================


class ChantiersUniteListView(RoleRequiredMixin, ListView):
    """Liste les unités en chantier pour le commercial."""
    model = Unite
    template_name = 'catalog/chantiers_unites_list.html'
    context_object_name = 'unites'
    required_roles = ["COMMERCIAL", "ADMIN"]
    paginate_by = 20

    def get_queryset(self):
        """Afficher les unités réservées ou vendues (en chantier) - VENTE UNIQUEMENT"""
        from core.choices import UniteStatus, OperationType

        user = self.request.user
        qs = Unite.objects.filter(
            statut_disponibilite__in=[UniteStatus.RESERVE, UniteStatus.VENDU],
            programme__type_operation=OperationType.VENTE  # 🏠 Exclure locations
        ).select_related('programme', 'modele_bien').prefetch_related('avancements_chantier')

        # 🔒 ADMIN voit tous les chantiers, COMMERCIAL seulement les siens
        if is_admin_user(user):
            return qs

        return qs.filter(programme__contact_commercial=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pour chaque unité, récupérer le dernier avancement
        for unite in context['unites']:
            if unite.avancements_chantier.exists():
                unite.dernier_avancement = unite.avancements_chantier.first()
            else:
                unite.dernier_avancement = None
        return context


class AvancementChantierUniteDetailView(RoleRequiredMixin, DetailView):
    """Détail d'un avancement chantier unité avec photos."""
    model = AvancementChantierUnite
    template_name = 'catalog/avancement_chantier_unite_detail.html'
    context_object_name = 'avancement'
    required_roles = ["COMMERCIAL", "ADMIN"]
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        user = self.request.user
        qs = AvancementChantierUnite.objects.select_related(
            'unite', 'unite__programme', 'reservation'
        ).prefetch_related('photos')

        if is_admin_user(user):
            return qs

        return qs.filter(unite__programme__contact_commercial=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        avancement = self.get_object()
        context['photos'] = avancement.photos.all().order_by('-pris_le')
        # Historique des avancements pour cette unité
        context['historique'] = avancement.unite.avancements_chantier.exclude(
            pk=avancement.pk
        ).order_by('-date_pointage')[:5]
        # Messages des clients pour cet avancement (exclure les messages supprimés pour cet utilisateur)
        context['messages'] = avancement.messages.exclude(supprime_par=self.request.user).order_by('created_at')
        return context


class AvancementChantierUniteCreateView(RoleRequiredMixin, CreateView):
    """Ajouter un avancement chantier pour une unité."""
    model = AvancementChantierUnite
    form_class = AvancementChantierUniteForm
    template_name = 'catalog/avancement_chantier_unite_form.html'
    required_roles = ["COMMERCIAL", "ADMIN"]

    def get_initial(self):
        """Pré-remplir les champs depuis les paramètres URL."""
        from core.choices import OperationType
        initial = super().get_initial()
        
        # Récupérer l'unité depuis le QueryString (?unite=<id>)
        unite_id = self.request.GET.get('unite')
        if unite_id:
            try:
                unite = Unite.objects.get(id=unite_id)
                
                # 🏠 BLOQUER les programmes de location
                if unite.programme.type_operation == OperationType.LOCATION:
                    raise PermissionDenied("Le suivi de chantier n'est pas disponible pour les programmes de location.")
                
                user = self.request.user
                if not is_admin_user(user):
                    if unite.programme.contact_commercial != user:
                        raise PermissionDenied("Accès refusé à cette unité.")
                initial['unite'] = unite
                
                # Si l'unité a une réservation confirmée/signée, la pré-sélectionner
                from sales.models import Reservation
                reservation = Reservation.objects.filter(
                    unite=unite,
                    statut__in=['confirmee', 'en_cours']  # Seulement les réservations actives
                ).first()
                if reservation:
                    initial['reservation'] = reservation
                    
            except Unite.DoesNotExist:
                pass
        
        return initial

    def get_context_data(self, **kwargs):
        from core.choices import OperationType
        context = super().get_context_data(**kwargs)
        # Récupérer l'unité si passée en paramètre (pour affichage)
        unite_id = self.request.GET.get('unite')
        if unite_id:
            try:
                unite = Unite.objects.get(id=unite_id)
                
                # 🏠 BLOQUER les programmes de location
                if unite.programme.type_operation == OperationType.LOCATION:
                    raise PermissionDenied("Le suivi de chantier n'est pas disponible pour les programmes de location.")
                
                user = self.request.user
                if not is_admin_user(user):
                    if unite.programme.contact_commercial != user:
                        raise PermissionDenied("Accès refusé à cette unité.")
                context['initial_unite'] = unite
            except Unite.DoesNotExist:
                pass
        return context

    def get_form(self, form_class=None):
        from core.choices import OperationType
        form = super().get_form(form_class)
        user = self.request.user
        if not is_admin_user(user):
            # 🏠 Filtrer uniquement les unités de VENTE du commercial
            form.fields['unite'].queryset = Unite.objects.filter(
                programme__contact_commercial=user,
                programme__type_operation=OperationType.VENTE
            )
            from sales.models import Reservation
            form.fields['reservation'].queryset = Reservation.objects.filter(
                unite__programme__contact_commercial=user,
                unite__programme__type_operation=OperationType.VENTE
            )
        else:
            # 🏠 Admin : filtrer uniquement les unités de VENTE
            form.fields['unite'].queryset = Unite.objects.filter(
                programme__type_operation=OperationType.VENTE
            )
            from sales.models import Reservation
            form.fields['reservation'].queryset = Reservation.objects.filter(
                unite__programme__type_operation=OperationType.VENTE
            )
        return form

    def form_valid(self, form):
        user = self.request.user
        unite = form.cleaned_data.get('unite')
        reservation = form.cleaned_data.get('reservation')
        if not is_admin_user(user):
            if unite and unite.programme.contact_commercial != user:
                raise PermissionDenied("Vous ne pouvez pas créer d'avancement pour cette unité.")
            if reservation and reservation.unite.programme.contact_commercial != user:
                raise PermissionDenied("Vous ne pouvez pas associer cette réservation.")

        # Sauvegarder l'avancement d'abord
        avancement = form.save()
        
        # IMPORTANT: Assigner self.object pour que get_success_url() fonctionne
        self.object = avancement
        
        # Gérer l'upload des photos
        photos = self.request.FILES.getlist('photos')
        if photos:
            for photo in photos:
                PhotoChantierUnite.objects.create(
                    avancement=avancement,
                    image=photo,
                    pris_le=datetime.now(),
                    description=f"Photo {avancement.etape}"
                )
        
        messages.success(self.request, f"Avancement chantier ajouté avec succès ({len(photos)} photo(s)).")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('avancement_detail', kwargs={'pk': self.object.pk})


class AvancementChantierUniteUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier un avancement chantier unité."""
    model = AvancementChantierUnite
    form_class = AvancementChantierUniteForm
    template_name = 'catalog/avancement_chantier_unite_form.html'
    required_roles = ["COMMERCIAL", "ADMIN"]

    def get_queryset(self):
        user = self.request.user
        qs = AvancementChantierUnite.objects.select_related('unite', 'unite__programme', 'reservation')
        if is_admin_user(user):
            return qs
        return qs.filter(unite__programme__contact_commercial=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter les photos existantes au contexte
        context['existing_photos'] = self.object.photos.all()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not is_admin_user(user):
            form.fields['unite'].queryset = Unite.objects.filter(programme__contact_commercial=user)
            from sales.models import Reservation
            form.fields['reservation'].queryset = Reservation.objects.filter(
                unite__programme__contact_commercial=user
            )
        return form

    def form_valid(self, form):
        user = self.request.user
        unite = form.cleaned_data.get('unite')
        reservation = form.cleaned_data.get('reservation')
        if not is_admin_user(user):
            if unite and unite.programme.contact_commercial != user:
                raise PermissionDenied("Vous ne pouvez pas modifier cet avancement.")
            if reservation and reservation.unite.programme.contact_commercial != user:
                raise PermissionDenied("Réservation non autorisée.")
        
        # Sauvegarder les modifications
        avancement = form.save()
        
        # Ajouter de nouvelles photos si uploadées
        photos = self.request.FILES.getlist('photos')
        if photos:
            for photo in photos:
                PhotoChantierUnite.objects.create(
                    avancement=avancement,
                    image=photo,
                    pris_le=datetime.now(),
                    description=f"Photo {avancement.etape}"
                )
            messages.success(self.request, f"Avancement mis à jour. {len(photos)} nouvelle(s) photo(s) ajoutée(s).")
        else:
            messages.success(self.request, "Avancement chantier mis à jour.")
        
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('avancement_detail', kwargs={'pk': self.object.pk})

