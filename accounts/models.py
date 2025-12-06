import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Role(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    libelle = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"

    def __str__(self) -> str:
        return f"{self.code} - {self.libelle}"


class User(AbstractUser):
    # ID en UUID (clé primaire)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # On utilise l'email comme identifiant unique pour la connexion.
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Nom d'utilisateur interne (optionnel).",
        error_messages={
            "unique": "Un utilisateur avec ce nom existe déjà.",
        },
    )
    email = models.EmailField("adresse email", unique=True)
    telephone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Numéro de téléphone",
        verbose_name="Téléphone"
    )
    roles = models.ManyToManyField(Role, related_name="utilisateurs", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self) -> str:
        full_name = self.get_full_name().strip()
        if full_name:
            return f"{full_name} <{self.email}>"
        return self.email

    def has_role(self, code: str) -> bool:
        if not code:
            return False
        return self.roles.filter(code__iexact=code).exists()

    @property
    def is_client(self) -> bool:
        return self.has_role("CLIENT")

    @property
    def is_commercial(self) -> bool:
        return self.has_role("COMMERCIAL")

    @property
    def is_admin_scindongo(self) -> bool:
        return self.has_role("ADMIN")
