from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import (
    LoginForm, RegisterForm, UserManagementForm, UserCreationFormWithPassword,
    ClientProfileForm, ClientChangePasswordForm
)
from .mixins import RoleRequiredMixin
from sales.utils import get_pending_unite_and_clear

User = get_user_model()


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


# === Gestion des utilisateurs (ADMIN uniquement) ===

class UserListView(RoleRequiredMixin, ListView):
    """Liste des utilisateurs (ADMIN uniquement)"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    required_roles = ["ADMIN"]
    paginate_by = 20

    def get_queryset(self):
        return User.objects.all().prefetch_related('roles').order_by('-date_joined')


class UserCreateView(RoleRequiredMixin, CreateView):
    """Créer un nouvel utilisateur (ADMIN uniquement)"""
    model = User
    form_class = UserCreationFormWithPassword
    template_name = 'accounts/user_form.html'
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        messages.success(self.request, f"Utilisateur {form.cleaned_data['username']} créé avec succès.")
        return super().form_valid(form)


class UserUpdateView(RoleRequiredMixin, UpdateView):
    """Modifier un utilisateur (ADMIN uniquement)"""
    model = User
    form_class = UserManagementForm
    template_name = 'accounts/user_form.html'
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        messages.success(self.request, f"Utilisateur {form.cleaned_data['username']} modifié avec succès.")
        return super().form_valid(form)


class UserDeleteView(RoleRequiredMixin, DeleteView):
    """Supprimer un utilisateur (ADMIN uniquement)"""
    model = User
    required_roles = ["ADMIN"]
    success_url = reverse_lazy('user_list')

    def post(self, request, *args, **kwargs):
        """Suppression directe sans page de confirmation"""
        messages.success(request, "Utilisateur supprimé avec succès.")
        return self.delete(request, *args, **kwargs)


# === Gestion du profil client ===

class ClientProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Modifier le profil du client (prénom, nom, email)"""
    model = User
    form_class = ClientProfileForm
    template_name = 'accounts/edit_profile.html'
    success_url = reverse_lazy('client_dashboard')
    
    def get_object(self, queryset=None):
        """Retourner l'utilisateur connecté"""
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, "✅ Votre profil a été mis à jour avec succès.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Modifier mon profil"
        return context


class ClientChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    """Changer le mot de passe du client"""
    form_class = ClientChangePasswordForm
    template_name = 'accounts/change_password.html'
    success_url = reverse_lazy('client_dashboard')
    
    def form_valid(self, form):
        messages.success(self.request, "✅ Votre mot de passe a été changé avec succès.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Changer mon mot de passe"
        return context
