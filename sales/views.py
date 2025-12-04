from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from accounts.mixins import RoleRequiredMixin
from accounts.models import User, Role
from catalog.models import Unite
from .models import Client, Reservation, Paiement
from .forms import ReservationForm, PaiementForm
from .utils import set_pending_unite
from .mixins import ReservationRequiredMixin, FinancementFormMixin, ContratFormMixin, PaiementFormMixin
from core.utils import audit_log

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum

from catalog.models import Programme, Unite
from sales.models import Reservation, Paiement, Financement, BanquePartenaire



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
    """Démarre le processus de réservation pour une unité."""

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
            reservation = form.save(commit=False)
            reservation.client = client
            reservation.unite = unite
            reservation.statut = "en_cours"  # Statut initial
            reservation.save()
            # Mettre à jour le statut de l'unité à "réservé"
            unite.statut_disponibilite = "reserve"
            unite.save(update_fields=["statut_disponibilite"])
            audit_log(request.user, reservation, "reservation_create", {"acompte": str(reservation.acompte)}, request)
            # Rediriger vers une page de confirmation, pas directement au paiement
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
        reservation = get_object_or_404(Reservation, id=reservation_id, client__user=self.request.user)
        ctx['reservation'] = reservation
        ctx['banques'] = BanquePartenaire.objects.all()
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
