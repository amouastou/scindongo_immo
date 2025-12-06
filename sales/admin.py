from django.contrib import admin
from .models import Client, Reservation, ReservationDocument, Contrat, Paiement, BanquePartenaire, Financement, Echeance


class ReservationDocumentInline(admin.TabularInline):
    """Inline pour voir/gérer documents dans la fiche Réservation"""
    model = ReservationDocument
    extra = 0
    fields = ('document_type', 'statut', 'raison_rejet', 'verifie_par', 'verifie_le', 'fichier')
    readonly_fields = ('created_at', 'updated_at', 'fichier')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "telephone", "email", "kyc_statut", "created_at")
    search_fields = ("nom", "prenom", "telephone", "email")
    list_filter = ("kyc_statut",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("client", "unite", "date_reservation", "acompte", "statut", "created_at")
    list_filter = ("statut", "date_reservation")
    search_fields = ("client__nom", "client__prenom", "unite__reference_lot")
    autocomplete_fields = ("client", "unite")
    inlines = [ReservationDocumentInline]


@admin.register(ReservationDocument)
class ReservationDocumentAdmin(admin.ModelAdmin):
    list_display = ("reservation", "document_type", "statut", "verifie_par", "verifie_le", "created_at")
    list_filter = ("document_type", "statut", "created_at")
    search_fields = ("reservation__client__nom", "reservation__client__prenom")
    readonly_fields = ("reservation", "document_type", "fichier", "created_at", "updated_at")
    
    def save_model(self, request, obj, form, change):
        """Quand un commercial valide un document, on log qui et quand"""
        if change and obj.statut == 'valide' and not obj.verifie_par:
            obj.verifie_par = request.user
            from django.utils import timezone
            obj.verifie_le = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ("numero", "reservation", "statut", "signe_le", "created_at")
    list_filter = ("statut",)
    search_fields = ("numero",)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("reservation", "montant", "date_paiement", "moyen", "source", "statut", "created_at")
    list_filter = ("statut", "moyen", "source")
    search_fields = ("reservation__client__nom", "reservation__client__prenom")


@admin.register(BanquePartenaire)
class BanquePartenaireAdmin(admin.ModelAdmin):
    list_display = ("nom", "code_banque", "contact", "created_at")
    search_fields = ("nom", "code_banque")


@admin.register(Financement)
class FinancementAdmin(admin.ModelAdmin):
    list_display = ("reservation", "banque", "type", "montant", "statut", "created_at")
    list_filter = ("statut", "banque")
    search_fields = ("reservation__client__nom", "reservation__client__prenom")


@admin.register(Echeance)
class EcheanceAdmin(admin.ModelAdmin):
    list_display = ("financement", "date_echeance", "montant_total", "statut", "created_at")
    list_filter = ("statut", "date_echeance")
