from django.views.generic import TemplateView, ListView, DetailView, UpdateView, DeleteView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from accounts.mixins import RoleRequiredMixin
from .models import Programme, Unite
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
