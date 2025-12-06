from django.views.generic import TemplateView, ListView, DetailView, UpdateView, DeleteView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from accounts.mixins import RoleRequiredMixin
from .models import Programme, Unite, TypeBien, ModeleBien, AvancementChantierUnite, PhotoChantierUnite, MessageChantier
from .forms import ProgrammeForm, AvancementChantierUniteForm
from datetime import datetime


class HomeView(TemplateView):
    template_name = 'public/home.html'


class ProgrammeListView(ListView):
    model = Programme
    template_name = 'catalog/programme_list.html'
    context_object_name = 'programmes'

    def get_queryset(self):
        # Affiche tous les programmes sans filtre caché
        return Programme.objects.all().order_by("nom")


class ProgrammeDetailView(DetailView):
    model = Programme
    template_name = 'catalog/programme_detail.html'
    context_object_name = 'programme'


class UniteDetailView(DetailView):
    model = Unite
    template_name = 'catalog/unite_detail.html'
    context_object_name = 'unite'


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
        
        # Statistiques globales - basées sur les réservations confirmées
        from sales.models import Reservation
        from django.db.models import Q
        
        all_biens = Unite.objects.all()
        context['total_biens'] = all_biens.count()
        
        # Biens avec réservation confirmée = "Vendus/Livrés"
        biens_avec_resa_confirmee = all_biens.filter(
            reservations__statut='confirmee'
        ).distinct().count()
        context['biens_vendus'] = biens_avec_resa_confirmee
        
        # Biens avec réservation EN COURS ou non-annulée (mais pas confirmée) = "Réservés"
        biens_avec_resa_encours = all_biens.filter(
            Q(reservations__statut='en_cours') | 
            Q(reservations__statut='reserve')
        ).exclude(
            reservations__statut='annulee'
        ).distinct().count()
        context['biens_reserves'] = biens_avec_resa_encours
        
        # Biens disponibles = biens sans réservation active (ou avec seulement des annulées)
        context['biens_disponibles'] = context['total_biens'] - context['biens_vendus'] - context['biens_reserves']
        
        return context

# === Pages publiques supplémentaires ===

class PourquoiInvestirView(TemplateView):
    """
    Page marketing expliquant pourquoi investir avec SCINDONGO Immo
    (conforme à l'esprit du document de cadrage).
    """
    template_name = 'public/pourquoi_investir.html'


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


class ProgrammeCreateView(RoleRequiredMixin, CreateView):
    """
    Vue pour créer un nouveau programme (accessible aux ADMIN et COMMERCIAL)
    """
    model = Programme
    template_name = 'catalog/programme_form.html'
    form_class = ProgrammeForm
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('programme_list')


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
    """Liste des unités (ADMIN/COMMERCIAL)"""
    model = Unite
    template_name = 'catalog/unite_list.html'
    context_object_name = 'unites'
    required_roles = ["ADMIN", "COMMERCIAL"]
    paginate_by = 20
    
    def get_queryset(self):
        return Unite.objects.select_related('programme', 'modele_bien', 'modele_bien__type_bien').all()


class UniteCreateView(RoleRequiredMixin, CreateView):
    """Créer une unité (ADMIN/COMMERCIAL)"""
    model = Unite
    template_name = 'catalog/unite_form.html'
    fields = ['programme', 'modele_bien', 'reference_lot', 'prix_ttc', 'statut_disponibilite', 'gps_lat', 'gps_lng', 'image']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('unite_list')


class UniteUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier une unité (ADMIN/COMMERCIAL)"""
    model = Unite
    template_name = 'catalog/unite_form.html'
    fields = ['programme', 'modele_bien', 'reference_lot', 'prix_ttc', 'statut_disponibilite', 'gps_lat', 'gps_lng', 'image']
    required_roles = ["ADMIN", "COMMERCIAL"]
    success_url = reverse_lazy('unite_list')


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
        """Afficher les unités réservées ou vendues (en chantier)"""
        from core.choices import UniteStatus
        return Unite.objects.filter(
            statut_disponibilite__in=[UniteStatus.RESERVE, UniteStatus.VENDU]
        ).select_related('programme', 'modele_bien').prefetch_related('avancements_chantier')

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
        return AvancementChantierUnite.objects.select_related(
            'unite', 'unite__programme', 'reservation'
        ).prefetch_related('photos')

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
        initial = super().get_initial()
        
        # Récupérer l'unité depuis le QueryString (?unite=<id>)
        unite_id = self.request.GET.get('unite')
        if unite_id:
            try:
                unite = Unite.objects.get(id=unite_id)
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
        context = super().get_context_data(**kwargs)
        # Récupérer l'unité si passée en paramètre (pour affichage)
        unite_id = self.request.GET.get('unite')
        if unite_id:
            try:
                context['initial_unite'] = Unite.objects.get(id=unite_id)
            except Unite.DoesNotExist:
                pass
        return context

    def form_valid(self, form):
        # Sauvegarder l'avancement d'abord
        avancement = form.save()
        
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter les photos existantes au contexte
        context['existing_photos'] = self.object.photos.all()
        return context

    def form_valid(self, form):
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

