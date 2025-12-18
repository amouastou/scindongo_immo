"""
Middleware d'audit pour tracer automatiquement toutes les actions des utilisateurs.
"""

import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from core.models import JournalAudit
from core.utils import get_client_ip


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware qui trace automatiquement toutes les requêtes HTTP.
    """
    
    # URLs à ignorer pour éviter trop de bruit
    IGNORED_PATHS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/__debug__/',
    ]
    
    # Méthodes à tracer (on ignore généralement les GET sauf pour des ressources sensibles)
    TRACED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Paths sensibles à tracer même en GET
    SENSITIVE_PATHS = [
        '/admin/',
        '/api/reservations/',
        '/api/paiements/',
        '/api/contrats/',
        '/api/financements/',
        '/api/clients/',
        '/client/reservations/',
        '/commercial/reservations/',
    ]
    
    def process_request(self, request):
        """Enregistrer le début du traitement de la requête"""
        request._audit_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
        Tracer la requête après traitement si elle est pertinente.
        """
        # Ignorer les paths statiques
        if any(request.path.startswith(ignored) for ignored in self.IGNORED_PATHS):
            return response
        
        # Décider si on trace cette requête
        should_trace = False
        categorie = "data_read"
        
        # Tracer toutes les méthodes de modification
        if request.method in self.TRACED_METHODS:
            should_trace = True
            if request.method == 'POST':
                categorie = "data_create"
            elif request.method in ['PUT', 'PATCH']:
                categorie = "data_update"
            elif request.method == 'DELETE':
                categorie = "data_delete"
        
        # Tracer les GET sur des ressources sensibles
        elif request.method == 'GET':
            if any(request.path.startswith(sensitive) for sensitive in self.SENSITIVE_PATHS):
                should_trace = True
                categorie = "data_read"
        
        # Si on doit tracer
        if should_trace:
            self._create_audit_log(request, response, categorie)
        
        return response
    
    def _create_audit_log(self, request, response, categorie):
        """Créer une entrée d'audit pour cette requête"""
        try:
            # Déterminer le résultat basé sur le code HTTP
            if 200 <= response.status_code < 300:
                resultat = "success"
            elif 400 <= response.status_code < 500:
                resultat = "failure"
            elif 500 <= response.status_code:
                resultat = "failure"
            else:
                resultat = "pending"
            
            # Extraire les données de la requête (attention à la sensibilité)
            payload = {
                "status_code": response.status_code,
                "content_length": len(response.content) if hasattr(response, 'content') else 0,
            }
            
            # Ajouter le temps de traitement si disponible
            if hasattr(request, '_audit_start_time'):
                duration = time.time() - request._audit_start_time
                payload["duration_seconds"] = round(duration, 3)
            
            # Extraire les paramètres POST (masquer les mots de passe)
            if request.method == 'POST' and hasattr(request, 'POST'):
                post_data = dict(request.POST)
                # Masquer les champs sensibles
                sensitive_fields = ['password', 'password1', 'password2', 'old_password', 'new_password']
                for field in sensitive_fields:
                    if field in post_data:
                        post_data[field] = '***MASKED***'
                payload["post_data"] = post_data
            
            # Créer l'entrée d'audit
            JournalAudit.objects.create(
                acteur=request.user if request.user.is_authenticated else None,
                objet_type="HttpRequest",
                objet_id=None,
                action=f"{request.method} {request.path}",
                categorie=categorie,
                resultat=resultat,
                payload=payload,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255] or None,
                session_key=request.session.session_key if hasattr(request, 'session') and request.session.session_key else None,
                methode_http=request.method or None,
                url_path=request.path[:500] or None,
            )
        except Exception as e:
            # Ne jamais faire échouer une requête à cause de l'audit
            # En production, on pourrait logger cette erreur ailleurs
            pass


# ========================================
# SIGNAUX D'AUTHENTIFICATION
# ========================================

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Tracer les connexions réussies"""
    try:
        # S'assurer que la session est sauvegardée avant d'accéder à session_key
        if not request.session.session_key:
            request.session.save()
        
        JournalAudit.objects.create(
            acteur=user,
            objet_type="User",
            objet_id=user.id,
            action="user_login",
            categorie="authentication",
            resultat="success",
            payload={
                "email": user.email,
                "roles": [role.code for role in user.roles.all()],
            },
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255] or None,
            session_key=request.session.session_key or None,
            methode_http=request.method or None,
            url_path=request.path[:500] or None,
        )
    except Exception:
        pass


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Tracer les déconnexions"""
    try:
        JournalAudit.objects.create(
            acteur=user,
            objet_type="User",
            objet_id=user.id if user else None,
            action="user_logout",
            categorie="authentication",
            resultat="success",
            payload={
                "email": user.email if user else "unknown",
            },
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255] or None,
            session_key=request.session.session_key if hasattr(request, 'session') else None,
            methode_http=request.method or None,
            url_path=request.path[:500] or None,
        )
    except Exception:
        pass


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Tracer les tentatives de connexion échouées"""
    try:
        session_key = None
        if request and hasattr(request, 'session'):
            if not request.session.session_key:
                request.session.save()
            session_key = request.session.session_key
        
        JournalAudit.objects.create(
            acteur=None,
            objet_type="User",
            objet_id=None,
            action="user_login_failed",
            categorie="authentication",
            resultat="failure",
            payload={
                "email": credentials.get('username', 'unknown'),  # USERNAME_FIELD='email'
                "reason": "invalid_credentials",
            },
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255] if request else None,
            session_key=session_key,
            methode_http=request.method if request else None,
            url_path=request.path[:500] if request else None,
        )
    except Exception:
        pass
