import uuid
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from core.choices import ProgrammeStatus, UniteStatus, StatutChantier


class Programme(TimeStampedModel):
    """
    Programme immobilier (ex : Résidences Mame Diarra – Bayakh).
    """

    nom = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_principale = models.ImageField(upload_to="programmes/", null=True, blank=True)

    # Localisation
    adresse = models.CharField(max_length=255, blank=True)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Notaire / contact
    notaire_nom = models.CharField(max_length=255, blank=True)
    notaire_contact = models.CharField(max_length=255, blank=True)
    contact_commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programmes",
        limit_choices_to={"roles__code": "COMMERCIAL"}
    )
    
    # Statut du programme
    statut = models.CharField(
        max_length=20,
        choices=ProgrammeStatus.choices,
        default=ProgrammeStatus.BROUILLON,
    )

    date_livraison_prevue = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Programme"
        verbose_name_plural = "Programmes"
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom


class TypeBien(TimeStampedModel):
    """
    Typologie : appartement, villa, terrain, etc.
    """

    code = models.CharField(max_length=50, unique=True)
    libelle = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Type de bien"
        verbose_name_plural = "Types de biens"
        ordering = ("libelle",)

    def __str__(self) -> str:
        return f"{self.code} - {self.libelle}"


class ModeleBien(TimeStampedModel):
    """
    Modèle commercial (surface, prix de base, etc.).
    """

    type_bien = models.ForeignKey(
        TypeBien,
        on_delete=models.PROTECT,
        related_name="modeles",
    )
    nom_marketing = models.CharField(max_length=255)
    surface_hab_m2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    prix_base_ttc = models.DecimalField(max_digits=12, decimal_places=2)

    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Modèle de bien"
        verbose_name_plural = "Modèles de biens"
        ordering = ("nom_marketing",)

    def __str__(self) -> str:
        return f"{self.nom_marketing} ({self.type_bien.code})"


class Unite(TimeStampedModel):
    """
    Bien/unité physique : lot, appartement, villa, etc.
    """

    programme = models.ForeignKey(
        Programme,
        on_delete=models.PROTECT,
        related_name="unites",
    )
    modele_bien = models.ForeignKey(
        ModeleBien,
        on_delete=models.PROTECT,
        related_name="unites",
    )

    reference_lot = models.CharField(max_length=100)
    prix_ttc = models.DecimalField(max_digits=12, decimal_places=2)

    # Statut de disponibilité
    statut_disponibilite = models.CharField(
        max_length=20,
        choices=UniteStatus.choices,
        default=UniteStatus.DISPONIBLE,
    )

    # Statut de chantier (progression de construction)
    statut_chantier = models.CharField(
        max_length=20,
        choices=StatutChantier.choices,
        default=StatutChantier.NON_COMMENCE,
        help_text="Suivi de la progression de construction de l'unité"
    )

    # Caractéristiques techniques / commerciales dynamiques
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    caracteristiques = models.JSONField(default=dict, blank=True)

    image = models.ImageField(upload_to="unites/", null=True, blank=True)

    class Meta:
        verbose_name = "Unité"
        verbose_name_plural = "Unités"
        unique_together = ("programme", "reference_lot")
        ordering = ("programme", "reference_lot")

    def __str__(self) -> str:
        return f"{self.programme.nom} - {self.reference_lot}"
    
    def get_statut_reel(self):
        """
        Retourner le statut réel du bien basé sur les réservations.
        - Si réservation CONFIRMÉE : "vendu" (même si statut_disponibilite dit autre chose)
        - Si réservation en_cours/reserve : "reserve"
        - Sinon : retourner statut_disponibilite
        """
        from sales.models import Reservation
        
        # Vérifier si cette unité a une réservation confirmée
        if self.reservations.filter(statut='confirmee').exists():
            return 'vendu'
        
        # Vérifier si cette unité a une réservation en cours ou reserve
        if self.reservations.filter(statut__in=['en_cours', 'reserve']).exclude(statut='annulee').exists():
            return 'reserve'
        
        # Sinon, retourner le statut du modèle
        return self.statut_disponibilite


class EtapeChantier(TimeStampedModel):
    """
    Étapes du chantier pour un programme donné.
    """

    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name="etapes_chantier",
    )
    code = models.CharField(max_length=50)
    libelle = models.CharField(max_length=255)
    ordre = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Étape de chantier"
        verbose_name_plural = "Étapes de chantier"
        ordering = ("programme", "ordre")
        unique_together = ("programme", "code")

    def __str__(self) -> str:
        return f"{self.programme.nom} - {self.libelle}"


class AvancementChantier(TimeStampedModel):
    """
    Point d’avancement d’une étape : pourcentage, date, commentaire.
    """

    etape = models.ForeignKey(
        EtapeChantier,
        on_delete=models.CASCADE,
        related_name="avancements",
    )
    date_pointage = models.DateField()
    pourcentage = models.PositiveIntegerField()
    commentaire = models.TextField(blank=True)

    class Meta:
        verbose_name = "Avancement de chantier"
        verbose_name_plural = "Avancements de chantier"
        ordering = ("etape", "-date_pointage")

    def __str__(self):
        return f"{self.etape} - {self.pourcentage}%"


class PhotoChantier(TimeStampedModel):
    """
    Photos géolocalisées associées à un avancement.
    """

    avancement = models.ForeignKey(
        AvancementChantier,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="chantiers/")
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pris_le = models.DateTimeField()

    class Meta:
        verbose_name = "Photo de chantier"
        verbose_name_plural = "Photos de chantier"
        ordering = ("-pris_le",)

    def __str__(self):
        return f"Photo {self.id} - {self.avancement}"


class AvancementChantierUnite(TimeStampedModel):
    """
    Suivi d'avancement de chantier par unité individuelle (bien).
    Permet aux clients de suivre la progression après signature du contrat.
    Permet aux commercials de tracker les unités en construction.
    """

    unite = models.ForeignKey(
        Unite,
        on_delete=models.CASCADE,
        related_name="avancements_chantier",
    )
    # Lien optionnel à une réservation confirmée/contrat signé
    reservation = models.ForeignKey(
        'sales.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avancements_chantier",
    )

    # Étape / Libellé (ex: Fondations, Gros œuvre, Finitions, Livraison)
    etape = models.CharField(max_length=100)
    
    # Avancement
    date_pointage = models.DateField()
    pourcentage = models.PositiveIntegerField(
        default=0,
        help_text="Pourcentage d'avancement (0-100)"
    )
    commentaire = models.TextField(blank=True)

    class Meta:
        verbose_name = "Avancement chantier unité"
        verbose_name_plural = "Avancements chantier unités"
        ordering = ("unite", "-date_pointage")

    def __str__(self):
        return f"{self.unite.reference_lot} - {self.etape} ({self.pourcentage}%)"


class PhotoChantierUnite(TimeStampedModel):
    """
    Photos géolocalisées pour chaque avancement d'unité.
    """

    avancement = models.ForeignKey(
        AvancementChantierUnite,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="chantiers/unites/")
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pris_le = models.DateTimeField()
    description = models.TextField(blank=True, help_text="Description de la photo")

    class Meta:
        verbose_name = "Photo chantier unité"
        verbose_name_plural = "Photos chantier unités"
        ordering = ("-pris_le",)

    def __str__(self):
        return f"Photo {self.id} - {self.avancement}"


class MessageChantier(TimeStampedModel):
    """
    Messages entre client et commercial concernant un avancement de chantier.
    Le client pose des questions, le commercial répond.
    """
    avancement = models.ForeignKey(
        AvancementChantierUnite,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="Avancement concerné par le message"
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages_chantier",
        help_text="Auteur du message (client ou commercial)"
    )
    message = models.TextField(
        help_text="Contenu du message"
    )
    lu = models.BooleanField(
        default=False,
        help_text="Message lu par le destinataire"
    )
    reponse = models.TextField(
        blank=True,
        null=True,
        help_text="Réponse du commercial (optionnel)"
    )
    repondu_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reponses_messages_chantier",
        help_text="Commercial qui a répondu"
    )
    supprime_par = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="messages_chantier_supprimes",
        help_text="Utilisateurs qui ont supprimé ce message (soft delete)"
    )

    class Meta:
        verbose_name = "Message chantier"
        verbose_name_plural = "Messages chantier"
        ordering = ("created_at",)

    def __str__(self):
        return f"Message de {self.auteur.email} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
