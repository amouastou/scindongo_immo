from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, TemplateView, View
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
from .email_service import (
    send_verification_email, 
    is_verification_token_valid, 
    send_welcome_email
)
from .email_validator import validate_email_domain
from sales.utils import get_pending_unite_and_clear

User = get_user_model()


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def form_invalid(self, form):
        """Vérifier si le compte existe mais n'est pas vérifié"""
        email = form.cleaned_data.get('username')  # username field = email
        password = form.cleaned_data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                # Vérifier si le mot de passe est correct
                if user.check_password(password):
                    if not user.email_verified:
                        from django.utils.safestring import mark_safe
                        messages.warning(
                            self.request,
                            mark_safe(
                                "⚠️ <strong>Votre compte n'est pas encore activé.</strong><br>"
                                "Veuillez vérifier votre email et cliquer sur le lien de vérification.<br>"
                                "Si vous n'avez pas reçu l'email, "
                                "<a href='/comptes/registration-pending/' class='alert-link'>cliquez ici pour le renvoyer</a>."
                            )
                        )
                        return redirect('registration_pending')
            except User.DoesNotExist:
                pass
        
        return super().form_invalid(form)

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
        Validation en 3 étapes:
        1) Valider le domaine de l'email (DNS MX)
        2) Vérifier si l'adresse email spécifique existe (SMTP RCPT TO)
        3) Créer le compte et envoyer l'email de vérification
        """
        email = form.cleaned_data.get('email')
        
        # ÉTAPE 1: Validation du domaine AVANT de créer le compte
        domain_valid, domain_error = validate_email_domain(email)
        
        if not domain_valid:
            # Domaine invalide - afficher l'erreur immédiatement
            if domain_error == "domaine_inexistant":
                messages.error(
                    self.request,
                    f"❌ Le domaine de l'email '{email.split('@')[1]}' n'existe pas. "
                    "Veuillez vérifier l'orthographe de votre adresse email."
                )
            elif domain_error == "domaine_sans_mx":
                messages.error(
                    self.request,
                    f"❌ Le domaine '{email.split('@')[1]}' ne peut pas recevoir d'emails. "
                    "Veuillez utiliser une autre adresse email."
                )
            elif domain_error == "format_invalide":
                messages.error(
                    self.request,
                    "❌ Le format de l'adresse email est invalide."
                )
            
            # Logger l'échec
            from core.utils import audit_log
            audit_log(
                None,
                None,
                "user_registration_failed",
                {
                    "email": email,
                    "error_type": f"domain_validation_{domain_error}"
                },
                self.request,
                categorie="user_management",
                resultat="error"
            )
            
            # Rester sur la page d'inscription
            return self.form_invalid(form)
        
        # ÉTAPE 2: Vérification SMTP de l'adresse spécifique
        from .email_validator import verify_email_smtp
        
        email_exists, smtp_error = verify_email_smtp(email)
        
        if not email_exists:
            # L'adresse email a un problème
            if smtp_error == "email_inexistant":
                messages.error(
                    self.request,
                    f"❌ L'adresse email '{email}' n'existe pas. "
                    "Veuillez vérifier que vous avez saisi la bonne adresse."
                )
            elif smtp_error == "domaine_non_verifiable":
                messages.error(
                    self.request,
                    f"❌ Le domaine '{email.split('@')[1]}' ne permet pas de vérifier l'existence des adresses email. "
                    "Pour des raisons de sécurité, nous ne pouvons pas accepter les inscriptions avec ce domaine. "
                    "Veuillez utiliser une adresse Gmail, Yahoo, Orange ou un autre fournisseur."
                )
            else:
                messages.error(
                    self.request,
                    f"❌ Impossible de vérifier l'adresse email '{email}'. "
                    "Veuillez réessayer ou utiliser une autre adresse."
                )
            
            # Logger l'échec
            from core.utils import audit_log
            audit_log(
                None,
                None,
                "user_registration_failed",
                {
                    "email": email,
                    "error_type": f"smtp_verification_{smtp_error}"
                },
                self.request,
                categorie="user_management",
                resultat="error"
            )
            
            # Rester sur la page d'inscription
            return self.form_invalid(form)
        
        # ÉTAPE 3: Email valide - créer l'utilisateur
        user = form.save(commit=False)
        user.is_active = False  # Compte inactif jusqu'à vérification email
        user.save()
        
        # Ajouter le rôle CLIENT par défaut
        from .models import Role
        try:
            client_role = Role.objects.get(code='CLIENT')
            user.roles.add(client_role)
        except Role.DoesNotExist:
            pass
        
        # 4) Envoyer l'email de vérification
        email_sent, error_type = send_verification_email(user, self.request)
        
        if email_sent:
            # Succès : logger et rediriger
            from core.utils import audit_log
            audit_log(
                None,
                user,
                "user_registered",
                {"email": user.email},
                self.request,
                categorie="user_management",
                resultat="success"
            )
            
            messages.success(
                self.request,
                "✅ Un email de vérification a été envoyé à votre adresse. "
                "Veuillez cliquer sur le lien dans l'email pour activer votre compte."
            )
            return redirect('registration_pending')
        
        else:
            # Échec : supprimer le compte et afficher l'erreur
            user.delete()
            
            # Messages selon le type d'erreur
            if error_type == "email_inexistant":
                messages.error(
                    self.request,
                    "❌ Cette adresse email n'existe pas ou ne peut pas recevoir de messages. "
                    "Veuillez vérifier l'orthographe de votre adresse email et réessayer."
                )
            elif error_type == "email_refuse":
                messages.error(
                    self.request,
                    "❌ Cette adresse email a refusé notre message (boîte pleine ou bloquée). "
                    "Veuillez utiliser une autre adresse email."
                )
            elif error_type == "format_invalide":
                messages.error(
                    self.request,
                    "❌ Le format de l'adresse email est invalide. "
                    "Veuillez vérifier et réessayer."
                )
            else:
                messages.error(
                    self.request,
                    "❌ Impossible d'envoyer l'email de vérification. "
                    "Veuillez réessayer dans quelques instants ou utiliser une autre adresse email."
                )
            
            # Logger l'échec
            from core.utils import audit_log
            audit_log(
                None,
                None,
                "user_registration_failed",
                {
                    "email": form.cleaned_data.get('email'),
                    "error_type": error_type
                },
                self.request,
                categorie="user_management",
                resultat="error"
            )
            
            # Redirection vers page d'inscription pour réessayer
            return redirect('register')

    def get_success_url(self):
        # Ne devrait jamais être appelé car on redirige dans form_valid
        return reverse_lazy('registration_pending')


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


# === Vérification Email ===

from django.views.generic import TemplateView
from .email_service import is_verification_token_valid, send_welcome_email


class RegistrationPendingView(TemplateView):
    """Page affichée après inscription en attente de vérification email"""
    template_name = 'accounts/registration_pending.html'


class VerifyEmailView(TemplateView):
    """Vue pour vérifier l'email via le token"""
    template_name = 'accounts/email_verified.html'
    
    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        
        # Chercher l'utilisateur avec ce token
        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            messages.error(request, "❌ Lien de vérification invalide ou expiré.")
            return redirect('login')
        
        # Vérifier si le token est valide
        if not is_verification_token_valid(user, token):
            if user.email_verified:
                messages.info(request, "✓ Votre email est déjà vérifié. Vous pouvez vous connecter.")
            else:
                messages.error(
                    request,
                    "❌ Ce lien de vérification a expiré. "
                    "Un nouveau lien vous a été envoyé par email."
                )
                # Renvoyer un nouveau lien
                send_verification_email(user, request)
            return redirect('login')
        
        # Activer le compte
        user.email_verified = True
        user.is_active = True
        user.email_verification_token = None  # Supprimer le token
        user.save(update_fields=['email_verified', 'is_active', 'email_verification_token'])
        
        # Envoyer l'email de bienvenue
        send_welcome_email(user)
        
        # Logger la vérification
        from core.utils import audit_log
        audit_log(
            user,
            user,
            "email_verified",
            {"email": user.email},
            request,
            categorie="authentication",
            resultat="success"
        )
        
        messages.success(
            request,
            "✓ Votre email a été vérifié avec succès ! Vous pouvez maintenant vous connecter."
        )
        
        return super().get(request, *args, **kwargs)


class ResendVerificationEmailView(View):
    """Permet de renvoyer l'email de vérification - accessible sans être connecté"""
    
    def post(self, request, *args, **kwargs):
        # Récupérer l'email depuis le formulaire
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, "❌ Veuillez fournir une adresse email.")
            return redirect('registration_pending')
        
        try:
            user = User.objects.get(email=email, email_verified=False)
        except User.DoesNotExist:
            # Ne pas révéler si l'email existe ou pas (sécurité)
            messages.success(
                request,
                "✓ Si cette adresse existe et n'est pas vérifiée, un email a été envoyé."
            )
            return redirect('registration_pending')
        
        # Renvoyer l'email
        email_sent, error_type = send_verification_email(user, request)
        
        if email_sent:
            messages.success(
                request,
                "✓ Un nouvel email de vérification a été envoyé à votre adresse."
            )
        else:
            # Messages clairs selon le type d'erreur
            if error_type == "email_inexistant":
                messages.error(
                    request,
                    "❌ Cette adresse email n'existe pas ou ne peut pas recevoir de messages. "
                    "Veuillez vérifier l'orthographe de votre adresse email."
                )
            elif error_type == "email_refuse":
                messages.error(
                    request,
                    "❌ Cette adresse email a refusé notre message. "
                    "La boîte est peut-être pleine ou bloquée."
                )
            elif error_type == "format_invalide":
                messages.error(
                    request,
                    "❌ L'adresse email semble invalide. Veuillez vérifier l'orthographe."
                )
            else:
                messages.error(
                    request,
                    "❌ Impossible d'envoyer l'email. Veuillez réessayer dans quelques instants."
                )
        
        return redirect('registration_pending')


# === Gestion du profil pour COMMERCIAL ===

class CommercialProfileUpdateView(RoleRequiredMixin, LoginRequiredMixin, UpdateView):
    """Permet au commercial de modifier son profil personnel"""
    required_roles = ["COMMERCIAL"]
    model = User
    form_class = ClientProfileForm
    template_name = 'accounts/edit_profile_commercial.html'
    success_url = reverse_lazy('commercial_dashboard')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "✅ Votre profil a été mis à jour avec succès.")
        return super().form_valid(form)


class CommercialChangePasswordView(RoleRequiredMixin, LoginRequiredMixin, PasswordChangeView):
    """Permet au commercial de changer son mot de passe"""
    required_roles = ["COMMERCIAL"]
    form_class = ClientChangePasswordForm
    template_name = 'accounts/change_password_commercial.html'
    success_url = reverse_lazy('commercial_dashboard')

    def form_valid(self, form):
        messages.success(self.request, "✅ Votre mot de passe a été changé avec succès.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Changer mon mot de passe"
        return context
