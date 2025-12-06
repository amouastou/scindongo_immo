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


def audit_log(actor, obj, action: str, payload: dict | None = None, request=None):
    payload = payload or {}
    ip = None
    ua = ""
    if request is not None:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
    JournalAudit.objects.create(
        acteur=actor if actor and actor.is_authenticated else None,
        objet_type=obj.__class__.__name__,
        objet_id=getattr(obj, "id", None),
        action=action,
        payload=payload,
        ip_address=ip,
        user_agent=ua,
    )
