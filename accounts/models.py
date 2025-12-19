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


class CustomUserManager(UserManager):
    """Gestionnaire custom qui utilise l'email comme identifiant principal."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse email doit être renseignée")
        email = self.normalize_email(email)
        username = extra_fields.pop("username", None)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superuser doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superuser doit avoir is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


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
    
    # Vérification email
    email_verified = models.BooleanField(
        default=False,
        help_text="Email vérifié par le user"
    )
    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Token de vérification email"
    )
    email_verification_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date d'envoi du dernier email de vérification"
    )
    
    roles = models.ManyToManyField(Role, related_name="utilisateurs", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

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


class PasswordResetToken(TimeStampedModel):
    """
    Token sécurisé pour la réinitialisation de mot de passe.
    
    Caractéristiques de sécurité:
    - Token unique généré aléatoirement (32 bytes)
    - Expiration après 1 heure
    - Usage unique (is_used = True après utilisation)
    - Lié à un utilisateur spécifique
    - Supprimé automatiquement après utilisation
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='password_reset_tokens',
        verbose_name="Utilisateur"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Token de réinitialisation (32 bytes hex)"
    )
    is_used = models.BooleanField(
        default=False,
        help_text="Token déjà utilisé"
    )
    expires_at = models.DateTimeField(
        help_text="Date d'expiration du token (1h après création)"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP de l'utilisateur qui a demandé le reset"
    )
    
    class Meta:
        verbose_name = "Token de réinitialisation"
        verbose_name_plural = "Tokens de réinitialisation"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset token for {self.user.email} - {'Used' if self.is_used else 'Valid'}"
    
    def is_valid(self):
        """Vérifie si le token est encore valide"""
        from django.utils import timezone
        
        if self.is_used:
            return False
        
        if timezone.now() > self.expires_at:
            return False
        
        return True
    
    def mark_as_used(self):
        """Marque le token comme utilisé"""
        self.is_used = True
        self.save(update_fields=['is_used', 'updated_at'])
