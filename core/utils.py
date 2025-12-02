from .models import JournalAudit
from django.contrib.contenttypes.models import ContentType


def audit_log(actor, obj, action: str, payload: dict | None = None, request=None):
    payload = payload or {}
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get('REMOTE_ADDR')
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
