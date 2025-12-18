"""
Service d'envoi d'emails pour l'authentification.
"""

import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from smtplib import SMTPException, SMTPRecipientsRefused, SMTPSenderRefused

# Logger pour les erreurs d'email
logger = logging.getLogger(__name__)


def generate_verification_token():
    """Génère un token sécurisé pour la vérification email"""
    return secrets.token_urlsafe(32)


def send_verification_email(user, request):
    """
    Envoie un email de vérification à l'utilisateur.
    
    Args:
        user: Instance de User
        request: HttpRequest pour construire l'URL absolue
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        # Générer le token
        token = generate_verification_token()
        user.email_verification_token = token
        user.email_verification_sent_at = timezone.now()
        user.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        
        # Construire l'URL de vérification
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': token})
        )
        
        # Contexte pour le template
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': 'SCINDONGO Immo',
            'expiration_hours': 24,
        }
        
        # Rendu du template HTML
        html_message = render_to_string('accounts/emails/verify_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Envoi de l'email
        send_mail(
            subject='Vérifiez votre adresse email - SCINDONGO Immo',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email de vérification envoyé à {user.email}")
        return True, None
        
    except BadHeaderError as e:
        # En-têtes email invalides (injection possible)
        logger.error(f"BadHeaderError pour {user.email}: {e}")
        return False, "format_invalide"
    
    except SMTPRecipientsRefused as e:
        # Email refusé par le serveur (n'existe pas, boîte pleine, etc.)
        logger.error(f"SMTPRecipientsRefused pour {user.email}: {e}")
        # Vérifier si c'est l'erreur "email n'existe pas" (550 5.1.1)
        error_msg = str(e)
        if "550" in error_msg or "does not exist" in error_msg.lower():
            return False, "email_inexistant"
        return False, "email_refuse"
        
    except SMTPSenderRefused as e:
        # Expéditeur refusé (problème de configuration)
        logger.error(f"SMTPSenderRefused pour {user.email}: {e}")
        return False, "expediteur_refuse"
        
    except SMTPException as e:
        # Autres erreurs SMTP
        logger.error(f"SMTPException pour {user.email}: {e}")
        return False, "erreur_envoi"
        
    except Exception as e:
        # Autres erreurs
        logger.error(f"Erreur inattendue envoi email à {user.email}: {e}")
        return False, "erreur_inconnue"


def is_verification_token_valid(user, token):
    """
    Vérifie si le token de vérification est valide.
    
    Args:
        user: Instance de User
        token: Token à vérifier
    
    Returns:
        bool: True si valide, False sinon
    """
    # Vérifier que le token correspond
    if user.email_verification_token != token:
        return False
    
    # Vérifier que l'email n'est pas déjà vérifié
    if user.email_verified:
        return False
    
    # Vérifier l'expiration (24h)
    if user.email_verification_sent_at:
        expiration = user.email_verification_sent_at + timedelta(hours=24)
        if timezone.now() > expiration:
            return False
    
    return True


def send_welcome_email(user):
    """
    Envoie un email de bienvenue après vérification.
    
    Args:
        user: Instance de User
    
    Returns:
        bool: True si envoi réussi, False sinon
    """
    try:
        context = {
            'user': user,
            'site_name': 'SCINDONGO Immo',
            'login_url': settings.SITE_URL + reverse('login'),
        }
        
        html_message = render_to_string('accounts/emails/welcome_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject='Bienvenue sur SCINDONGO Immo !',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,  # Ne pas bloquer si l'email de bienvenue échoue
        )
        
        logger.info(f"Email de bienvenue envoyé à {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur envoi email de bienvenue à {user.email}: {e}")
        return False
