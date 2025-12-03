from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login  # important

from .forms import LoginForm, RegisterForm
from sales.utils import get_pending_unite_and_clear


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def get_success_url(self):
        """
        Redirection intelligente après login :
        1. Si un client venait pour réserver un lot → reprendre la réservation
        2. Sinon, rediriger selon le rôle :
           - CLIENT → dashboard client
           - COMMERCIAL → dashboard commercial
           - ADMIN → dashboard admin
        3. Sinon → accueil
        """
        request = self.request
        user = request.user
        
        # 1) Vérifier si une réservation était en attente
        unite_id = get_pending_unite_and_clear(request)
        if unite_id:
            return reverse_lazy('start_reservation', kwargs={'unite_id': unite_id})
        
        # 2) Redirection par rôle
        if user.is_client:
            return reverse_lazy('client_dashboard')
        elif user.is_commercial:
            return reverse_lazy('commercial_dashboard')
        elif user.is_admin_scindongo:
            return reverse_lazy('admin_dashboard')
        
        # 3) Sinon accueil
        return self.get_redirect_url() or reverse_lazy('home')


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('home')


class RegisterView(CreateView):
    template_name = 'accounts/register.html'
    form_class = RegisterForm

    def form_valid(self, form):
        """
        - on crée l'utilisateur
        - on l'authentifie et on le connecte
        - si une unité était en attente (réservation), on reprend le flux
        """
        # 1) Sauvegarde de l'utilisateur
        user = form.save()

        # 2) Authentification (USERNAME_FIELD = 'email', mais le backend attend "username")
        raw_password = form.cleaned_data["password1"]
        auth_user = authenticate(
            self.request,
            username=user.email,  # très important : username=, pas email=
            password=raw_password,
        )

        # 3) Connexion si OK
        if auth_user is not None:
            login(self.request, auth_user)

        # 4) Reprise éventuelle du flux de réservation
        unite_id = get_pending_unite_and_clear(self.request)
        if unite_id:
            return redirect('start_reservation', unite_id=unite_id)

        # 5) Sinon, retour à l'accueil
        return redirect('home')

    def get_success_url(self):
        # ne sera normalement pas utilisée car on fait déjà les redirects dans form_valid
        return reverse_lazy('home')
