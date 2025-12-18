from .models import JournalAudit
from django.contrib.contenttypes.models import ContentType


def get_client_ip(request):
    """
    Récupère l'adresse IP du client depuis la requête.
    
    Prend en compte les proxies (X-Forwarded-For).
    
    Args:
        request: HttpRequest Django
    
    Returns:
        str: Adresse IP du client
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def audit_log(
    actor,
    obj,
    action: str,
    payload: dict | None = None,
    request=None,
    categorie: str = "system",
    resultat: str = "success"
):
    """
    Enregistre une action dans le journal d'audit.
    
    Args:
        actor: Utilisateur ayant effectué l'action (User ou None pour système)
        obj: Objet concerné par l'action (modèle Django ou None)
        action: Nom de l'action (ex: "login", "create", "update", "delete")
        payload: Données supplémentaires (dict)
        request: HttpRequest Django (pour IP, user-agent, session, méthode, URL)
        categorie: Catégorie de l'action (voir AuditActionCategory)
        resultat: Résultat de l'action ("success", "failure", "partial", "pending")
    
    Returns:
        JournalAudit: L'entrée d'audit créée
    """
    payload = payload or {}
    ip = None
    ua = ""
    session_key = ""
    methode_http = ""
    url_path = ""
    
    # Extraire les infos de la requête
    if request is not None:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        session_key = request.session.session_key or ""
        methode_http = request.method
        url_path = request.path
    
    # Créer l'entrée d'audit
    return JournalAudit.objects.create(
        acteur=actor if actor and hasattr(actor, 'is_authenticated') and actor.is_authenticated else None,
        objet_type=obj.__class__.__name__ if obj else "System",
        objet_id=getattr(obj, "id", None),
        action=action,
        categorie=categorie,
        resultat=resultat,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
        session_key=session_key,
        methode_http=methode_http,
        url_path=url_path,
    )
