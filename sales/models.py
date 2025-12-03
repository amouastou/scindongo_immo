from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from catalog.models import Unite
from core.choices import (
    ReservationStatus,
    ContratStatus,
    PaiementStatus,
    FinancementStatus,
    MoyenPaiement,
)


class Client(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_profile',
    )
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=50)
    email = models.EmailField()
    kyc_statut = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Reservation(TimeStampedModel):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='reservations')
    unite = models.ForeignKey(Unite, on_delete=models.PROTECT, related_name='reservations')
    date_reservation = models.DateField(auto_now_add=True)
    acompte = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.EN_COURS,
    )

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"

    def __str__(self):
        return f"Réservation {self.id} - {self.client}"


class Contrat(TimeStampedModel):
    reservation = models.OneToOneField(Reservation, on_delete=models.PROTECT, related_name='contrat')
    numero = models.CharField(max_length=100, unique=True)
    statut = models.CharField(
        max_length=20,
        choices=ContratStatus.choices,
        default=ContratStatus.BROUILLON,
    )
    pdf = models.FileField(upload_to='contrats/', null=True, blank=True)
    signe_le = models.DateTimeField(null=True, blank=True)
    pdf_hash = models.CharField(max_length=128, blank=True)
    otp_logs = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Contrat"
        verbose_name_plural = "Contrats"

    def __str__(self):
        return self.numero


class Paiement(TimeStampedModel):
    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_paiement = models.DateField(auto_now_add=True)
    moyen = models.CharField(max_length=50, choices=MoyenPaiement.choices)
    source = models.CharField(max_length=50)
    statut = models.CharField(
        max_length=20,
        choices=PaiementStatus.choices,
        default=PaiementStatus.ENREGISTRE,
    )

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"{self.montant} - {self.reservation}"


class BanquePartenaire(TimeStampedModel):
    nom = models.CharField(max_length=255)
    code_banque = models.CharField(max_length=50, unique=True)
    contact = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nom


class Financement(TimeStampedModel):
    reservation = models.OneToOneField(Reservation, on_delete=models.PROTECT, related_name='financement')
    banque = models.ForeignKey(BanquePartenaire, on_delete=models.PROTECT, related_name='financements')
    type = models.CharField(max_length=50)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=20,
        choices=FinancementStatus.choices,
        default=FinancementStatus.SOUMIS,
    )

    class Meta:
        verbose_name = "Financement"
        verbose_name_plural = "Financements"

    def __str__(self):
        return f"{self.reservation} - {self.banque}"


class Echeance(TimeStampedModel):
    financement = models.ForeignKey(Financement, on_delete=models.CASCADE, related_name='echeances')
    date_echeance = models.DateField()
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=20,
        choices=FinancementStatus.choices,
        default=FinancementStatus.SOUMIS,
    )

    class Meta:
        verbose_name = "Échéance"
        verbose_name_plural = "Échéances"
        ordering = ("date_echeance",)

    def __str__(self):
        return f"{self.date_echeance} - {self.montant_total}"
