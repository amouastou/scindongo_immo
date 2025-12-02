import uuid
from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Document(TimeStampedModel):
    objet_type = models.CharField(max_length=50)
    objet_id = models.UUIDField()
    titre = models.CharField(max_length=255)
    fichier = models.FileField(upload_to='documents/')
    type_mime = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.titre


class JournalAudit(TimeStampedModel):
    acteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journaux_audit',
    )
    objet_type = models.CharField(max_length=50)
    objet_id = models.UUIDField()
    action = models.CharField(max_length=50)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.action} - {self.objet_type} ({self.objet_id})"
