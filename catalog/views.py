from django.views.generic import TemplateView, ListView, DetailView
from .models import Programme, Unite


class HomeView(TemplateView):
    template_name = 'public/home.html'


class ProgrammeListView(ListView):
    model = Programme
    template_name = 'catalog/programme_list.html'
    context_object_name = 'programmes'

    def get_queryset(self):
        qs = super().get_queryset().filter(statut='actif')
        type_bien = self.request.GET.get('type')
        if type_bien:
            qs = qs.filter(unites__modele_bien__type_bien__code=type_bien).distinct()
        return qs


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
