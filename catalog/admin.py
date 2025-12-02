from django.contrib import admin
from .models import (
    Programme,
    TypeBien,
    ModeleBien,
    Unite,
    EtapeChantier,
    AvancementChantier,
    PhotoChantier,
)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("nom", "statut", "adresse", "gps_lat", "gps_lng", "date_livraison_prevue", "created_at")
    list_filter = ("statut",)
    search_fields = ("nom", "description", "adresse", "notaire_nom", "contact_commercial_nom")


@admin.register(TypeBien)
class TypeBienAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "created_at")
    search_fields = ("code", "libelle")


@admin.register(ModeleBien)
class ModeleBienAdmin(admin.ModelAdmin):
    list_display = ("nom_marketing", "type_bien", "surface_hab_m2", "prix_base_ttc", "created_at")
    list_filter = ("type_bien",)
    search_fields = ("nom_marketing",)


@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = (
        "programme",
        "reference_lot",
        "modele_bien",
        "prix_ttc",
        "statut_disponibilite",
        "created_at",
    )
    list_filter = ("programme", "statut_disponibilite", "modele_bien__type_bien")
    search_fields = ("reference_lot",)
    autocomplete_fields = ("programme", "modele_bien")


@admin.register(EtapeChantier)
class EtapeChantierAdmin(admin.ModelAdmin):
    list_display = ("programme", "code", "libelle", "ordre", "created_at")
    list_filter = ("programme",)
    search_fields = ("code", "libelle")


@admin.register(AvancementChantier)
class AvancementChantierAdmin(admin.ModelAdmin):
    list_display = ("etape", "date_pointage", "pourcentage", "created_at")
    list_filter = ("etape__programme", "date_pointage")
    search_fields = ("commentaire",)


@admin.register(PhotoChantier)
class PhotoChantierAdmin(admin.ModelAdmin):
    list_display = ("avancement", "pris_le", "gps_lat", "gps_lng", "created_at")
    list_filter = ("avancement__etape__programme", "pris_le")
