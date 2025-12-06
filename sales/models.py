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
    
    # Champs pour l'annulation
    motif_annulation = models.TextField(blank=True, null=True, help_text="Motif de l'annulation par le commercial")
    annulee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations_annulees',
        help_text="Utilisateur qui a annulé la réservation"
    )
    annulee_le = models.DateTimeField(null=True, blank=True, help_text="Date/heure d'annulation")

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"

    def __str__(self):
        return f"Réservation {self.id} - {self.client}"
    
    def can_add_financement(self):
        """Vérifier qu'on peut ajouter un financement (réservation doit exister)"""
        return self.id is not None
    
    def can_sign_contrat(self):
        """Vérifier qu'on peut signer le contrat (réservation doit exister)"""
        return self.id is not None
    
    def can_add_paiement(self):
        """Vérifier qu'on peut ajouter un paiement (réservation doit exister)"""
        return self.id is not None
    
    def can_confirm_reservation(self):
        """
        Avant de confirmer la réservation, le contrat doit être signé
        """
        if not hasattr(self, 'contrat'):
            return False
        return self.contrat.statut == ContratStatus.SIGNE
    
    def can_cancel(self):
        """
        Vérifier si la réservation peut être annulée.
        Ne pas annuler si : statut=annulee|expiree OU contrat est signé
        """
        # Ne pas annuler si déjà annulée ou expirée
        if self.statut in [ReservationStatus.ANNULEE, ReservationStatus.EXPIREE]:
            return False
        
        # Ne pas annuler si contrat est signé (révocation légale complexe)
        if hasattr(self, 'contrat') and self.contrat.statut == ContratStatus.SIGNE:
            return False
        
        return True
    
    def can_delete(self):
        """
        Vérifier si la réservation peut être supprimée.
        Seulement si elle est annulée.
        """
        return self.statut == ReservationStatus.ANNULEE
    
    def cancel(self, user, motif):
        """
        Annuler la réservation et cascader les changements.
        Appelé par les views/API après validation.
        """
        from django.utils import timezone
        
        if not self.can_cancel():
            raise ValueError("Cette réservation ne peut pas être annulée.")
        
        # Marquer la réservation comme annulée
        self.statut = ReservationStatus.ANNULEE
        self.motif_annulation = motif
        self.annulee_par = user
        self.annulee_le = timezone.now()
        self.save()
        
        # La cascade sera gérée par le signal post_save


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
    otp_generated_at = models.DateTimeField(null=True, blank=True, help_text="Date et heure de génération du dernier OTP")

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


class ReservationDocument(TimeStampedModel):
    """Documents requis pour la réservation (CNI, photo, résidence)"""
    
    DOCUMENT_TYPES = [
        ('cni', 'CNI'),
        ('photo', 'Photo/Selfie'),
        ('residence', 'Preuve de résidence'),
    ]
    
    STATUS_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]
    
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES
    )
    fichier = models.FileField(upload_to='documents/reservations/%Y/%m/')
    statut = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='en_attente'
    )
    raison_rejet = models.TextField(blank=True)
    verifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservation_documents_verifies'
    )
    verifie_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('reservation', 'document_type')
        ordering = ['-created_at']
        verbose_name = "Document de réservation"
        verbose_name_plural = "Documents de réservation"

    def __str__(self):
        return f"{self.reservation} - {self.get_document_type_display()}"


class FinancementDocument(TimeStampedModel):
    """Documents requis pour le financement (brochure, CNI, bulletin salaire, RIB, attestation employeur)"""
    
    DOCUMENT_TYPES = [
        ('brochure', 'Brochure du programme'),
        ('cni', 'CNI'),
        ('bulletin_salaire', 'Bulletin de salaire'),
        ('rib_ou_iban', 'RIB ou IBAN'),
        ('attestation_employeur', "Attestation d'employeur"),
    ]
    
    STATUS_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]
    
    financement = models.ForeignKey(
        'Financement',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES
    )
    numero_ordre = models.IntegerField(
        default=1,
        help_text="Numéro d'ordre pour les documents multiples (ex: 1er, 2e, 3e bulletin)"
    )
    fichier = models.FileField(upload_to='documents/financements/%Y/%m/')
    statut = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='en_attente'
    )
    raison_rejet = models.TextField(blank=True)
    verifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financing_documents_verifies'
    )
    verifie_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('financement', 'document_type', 'numero_ordre')
        ordering = ['-created_at']
        verbose_name = "Document de financement"
        verbose_name_plural = "Documents de financement"

    def __str__(self):
        label = self.get_document_type_display()
        if self.numero_ordre > 1:
            suffixes = {1: "er", 2: "e", 3: "e"}
            suffix = suffixes.get(self.numero_ordre, "e")
            label = f"{label} ({self.numero_ordre}{suffix})"
        return f"{self.financement} - {label}"
    
    def get_document_label(self):
        """Retourne le libellé du document avec numéro d'ordre si applicable"""
        label = self.get_document_type_display()
        if self.numero_ordre > 1:
            suffixes = {1: "er", 2: "e", 3: "e"}
            suffix = suffixes.get(self.numero_ordre, "e")
            label = f"{label} ({self.numero_ordre}{suffix})"
        return label

