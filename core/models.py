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
    """
    Journal d'audit complet pour tracer toutes les actions des utilisateurs.
    """
    # Qui ?
    acteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journaux_audit',
        help_text="Utilisateur ayant effectué l'action (peut être null pour les actions système)"
    )
    
    # Quoi ?
    objet_type = models.CharField(
        max_length=50,
        help_text="Type d'objet concerné (ex: Reservation, Paiement, etc.)"
    )
    objet_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID de l'objet concerné (peut être null pour les actions globales)"
    )
    action = models.CharField(
        max_length=100,
        help_text="Action effectuée (ex: login, create, update, delete, etc.)"
    )
    
    # Catégorisation
    categorie = models.CharField(
        max_length=50,
        choices=[
            ('authentication', 'Authentification'),
            ('authorization', 'Autorisation'),
            ('data_create', 'Création'),
            ('data_read', 'Lecture'),
            ('data_update', 'Mise à jour'),
            ('data_delete', 'Suppression'),
            ('business_logic', 'Logique métier'),
            ('file_upload', 'Upload'),
            ('file_download', 'Téléchargement'),
            ('payment', 'Paiement'),
            ('contract', 'Contrat'),
            ('reservation', 'Réservation'),
            ('financing', 'Financement'),
            ('document', 'Document'),
            ('user_management', 'Gestion utilisateur'),
            ('system', 'Système'),
        ],
        default='system',
        help_text="Catégorie de l'action pour faciliter le filtrage"
    )
    
    # Résultat
    resultat = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Succès'),
            ('failure', 'Échec'),
            ('partial', 'Partiel'),
            ('pending', 'En attente'),
        ],
        default='success',
        help_text="Résultat de l'action"
    )
    
    # Contexte
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Données supplémentaires (changements, erreurs, etc.)"
    )
    
    # Traçabilité réseau
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Adresse IP de l'utilisateur"
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="",
        help_text="User-Agent du navigateur"
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default="",
        help_text="Clé de session Django pour tracer les sessions"
    )
    
    # Requête HTTP
    methode_http = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        default="",
        help_text="Méthode HTTP (GET, POST, PUT, DELETE, etc.)"
    )
    url_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        default="",
        help_text="Chemin URL de la requête"
    )

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['acteur', '-created_at']),
            models.Index(fields=['categorie', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['resultat', '-created_at']),
        ]

    def __str__(self):
        acteur_str = self.acteur.email if self.acteur else "Système"
        return f"[{self.get_categorie_display()}] {acteur_str} - {self.action} ({self.get_resultat_display()})"
