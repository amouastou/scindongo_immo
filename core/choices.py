"""
Énumérations des statuts métier – alignées sur le MCD.
Utiliser TextChoices plutôt que tuples pour une meilleure typage et maintenabilité.
"""

from django.db import models


# ========== PROGRAMMES ==========
class ProgrammeStatus(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    ACTIF = "actif", "Actif"
    ARCHIVE = "archive", "Archivé"


# ========== UNITÉS ==========
class UniteStatus(models.TextChoices):
    DISPONIBLE = "disponible", "Disponible"
    RESERVE = "reserve", "Réservé"
    VENDU = "vendu", "Vendu"
    LIVRE = "livre", "Livré"


# ========== STATUT CHANTIER (UNITÉ) ==========
class StatutChantier(models.TextChoices):
    NON_COMMENCE = "non_commence", "Non commencé"
    EN_COURS = "en_cours", "En cours"
    TERMINE = "termine", "Terminé"
    LIVRE = "livre", "Livré"


# ========== RÉSERVATIONS ==========
class ReservationStatus(models.TextChoices):
    EN_COURS = "en_cours", "En cours"
    CONFIRMEE = "confirmee", "Confirmée"
    ANNULEE = "annulee", "Annulée"
    EXPIREE = "expiree", "Expirée"


# ========== CONTRATS ==========
class ContratStatus(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    SIGNE = "signe", "Signé"
    ANNULE = "annule", "Annulé"


# ========== PAIEMENTS ==========
class PaiementStatus(models.TextChoices):
    ENREGISTRE = "enregistre", "Enregistré"
    VALIDE = "valide", "Validé"
    REJETE = "rejete", "Rejeté"


# ========== FINANCEMENT ==========
class FinancementStatus(models.TextChoices):
    SOUMIS = "soumis", "Soumis"
    EN_ETUDE = "en_etude", "En étude"
    ACCEPTE = "accepte", "Accepté"
    REFUSE = "refuse", "Refusé"
    CLOS = "clos", "Clos"


# ========== MOYENS DE PAIEMENT ==========
class MoyenPaiement(models.TextChoices):
    VIREMENT = "virement", "Virement bancaire"
    CHEQUE = "cheque", "Chèque"
    ESPECE = "espece", "Espèces"
    CARTE = "carte", "Carte bancaire"


# ========== RÔLES UTILISATEUR ==========
class UserRole(models.TextChoices):
    CLIENT = "CLIENT", "Client"
    COMMERCIAL = "COMMERCIAL", "Commercial"
    ADMIN = "ADMIN", "Administrateur"
