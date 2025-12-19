"""
Service pour la réinitialisation sécurisée du mot de passe.

Fonctionnalités:
- Génération de token sécurisé à usage unique
- Envoi d'email de réinitialisation
- Validation de token
- Notification après changement de mot de passe
"""
import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import PasswordResetToken, User


def generate_reset_token(user, request=None):
    """
    Génère un token de réinitialisation unique pour l'utilisateur.
    
    Args:
        user: Utilisateur pour qui générer le token
        request: Requête HTTP (pour récupérer l'IP)
    
    Returns:
        PasswordResetToken: Le token créé
    """
    # Invalider tous les anciens tokens non utilisés de cet utilisateur
    PasswordResetToken.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)
    
    # Générer un nouveau token (32 bytes = 64 caractères hex)
    token_value = secrets.token_hex(32)
    
    # Expiration dans 1 heure
    expires_at = timezone.now() + timedelta(hours=1)
    
    # Récupérer l'IP si disponible
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    # Créer le token
    reset_token = PasswordResetToken.objects.create(
        user=user,
        token=token_value,
        expires_at=expires_at,
        ip_address=ip_address
    )
    
    return reset_token


def send_password_reset_email(user, token, request):
    """
    Envoie l'email de réinitialisation de mot de passe.
    
    Args:
        user: Utilisateur concerné
        token: Token de réinitialisation
        request: Requête HTTP (pour construire l'URL complète)
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        # Construire l'URL de réinitialisation
        reset_url = request.build_absolute_uri(
            f'/comptes/reset-password/{token.token}/'
        )
        
        # Préparer le contexte de l'email
        context = {
            'user': user,
            'reset_url': reset_url,
            'expires_in_minutes': 60,
            'site_name': 'SCINDONGO Immo',
        }
        
        # Rendre le template HTML
        html_message = render_to_string('accounts/emails/password_reset.html', context)
        
        # Message texte brut
        text_message = f"""
Bonjour {user.get_full_name() or user.email},

Vous avez demandé la réinitialisation de votre mot de passe sur SCINDONGO Immo.

Cliquez sur le lien ci-dessous pour créer un nouveau mot de passe :
{reset_url}

⚠️ Ce lien est valable pendant 1 heure seulement.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email. Votre mot de passe actuel reste inchangé.

Cordialement,
L'équipe SCINDONGO Immo
        """
        
        # Envoyer l'email
        send_mail(
            subject='Réinitialisation de votre mot de passe - SCINDONGO Immo',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True, None
        
    except Exception as e:
        return False, str(e)


def send_password_changed_notification(user):
    """
    Envoie un email de notification après changement de mot de passe.
    
    Args:
        user: Utilisateur concerné
    
    Returns:
        bool: True si envoyé avec succès
    """
    try:
        # Préparer le contexte
        context = {
            'user': user,
            'site_name': 'SCINDONGO Immo',
        }
        
        # Rendre le template HTML
        html_message = render_to_string('accounts/emails/password_changed.html', context)
        
        # Message texte brut
        text_message = f"""
Bonjour {user.get_full_name() or user.email},

Votre mot de passe a été modifié avec succès sur SCINDONGO Immo.

Si vous n'êtes pas à l'origine de ce changement, contactez immédiatement notre support :
- Email : support@scindongo.com
- Téléphone : +221 XX XXX XX XX

Pour sécuriser votre compte :
- Utilisez un mot de passe unique et fort
- Ne partagez jamais votre mot de passe
- Activez la vérification en deux étapes si disponible

Cordialement,
L'équipe SCINDONGO Immo
        """
        
        # Envoyer l'email
        send_mail(
            subject='Votre mot de passe a été modifié - SCINDONGO Immo',
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Erreur envoi notification changement mot de passe : {e}")
        return False


def validate_reset_token(token_value):
    """
    Valide un token de réinitialisation.
    
    Args:
        token_value: La valeur du token à valider
    
    Returns:
        tuple: (token: PasswordResetToken or None, error: str or None)
    """
    try:
        token = PasswordResetToken.objects.get(token=token_value)
    except PasswordResetToken.DoesNotExist:
        return None, "Token invalide"
    
    if token.is_used:
        return None, "Ce lien a déjà été utilisé"
    
    if timezone.now() > token.expires_at:
        return None, "Ce lien a expiré"
    
    return token, None


def invalidate_all_sessions(user):
    """
    Invalide toutes les sessions actives d'un utilisateur.
    Force la déconnexion sur tous les appareils.
    
    Args:
        user: Utilisateur dont on veut invalider les sessions
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    
    # Récupérer toutes les sessions actives
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    
    # Pour chaque session, vérifier si elle appartient à cet utilisateur
    for session in active_sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.pk):
            # Supprimer la session
            session.delete()
