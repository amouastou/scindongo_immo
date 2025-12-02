from django.contrib import admin
from .models import Client, Reservation, Contrat, Paiement, BanquePartenaire, Financement, Echeance


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
