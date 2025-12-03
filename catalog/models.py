import uuid
from django.db import models
from core.models import TimeStampedModel
from core.choices import ProgrammeStatus, UniteStatus


class Programme(TimeStampedModel):
    """
    Programme immobilier (ex : Résidences Mame Diarra – Bayakh).
    """

    nom = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Localisation
    adresse = models.CharField(max_length=255, blank=True)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Notaire / contact
    notaire_nom = models.CharField(max_length=255, blank=True)
    notaire_contact = models.CharField(max_length=255, blank=True)
    contact_commercial_nom = models.CharField(max_length=255, blank=True)
    contact_commercial_tel = models.CharField(max_length=50, blank=True)
    
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
