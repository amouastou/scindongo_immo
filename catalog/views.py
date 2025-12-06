from django.views.generic import TemplateView, ListView, DetailView, UpdateView, DeleteView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from accounts.mixins import RoleRequiredMixin
from .models import Programme, Unite, TypeBien, ModeleBien
from .forms import ProgrammeForm


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
        
        # Statistiques globales
        all_biens = Unite.objects.all()
        context['total_biens'] = all_biens.count()
        context['biens_disponibles'] = all_biens.filter(statut_disponibilite='disponible').count()
        context['biens_reserves'] = all_biens.filter(statut_disponibilite='reserve').count()
        context['biens_vendus'] = all_biens.filter(statut_disponibilite__in=['vendu', 'livre']).count()
        
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

