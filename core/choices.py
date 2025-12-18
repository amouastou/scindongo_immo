"""
Énumérations des statuts métier – alignées sur le MCD.
Utiliser TextChoices plutôt que tuples pour une meilleure typage et maintenabilité.
"""

from django.db import models


# ========== TYPE D'OPÉRATION ==========
class OperationType(models.TextChoices):
    VENTE = "vente", "Vente"
    LOCATION = "location", "Location"


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


class PaiementType(models.TextChoices):
    ACOMPTE = "acompte", "Acompte"
    SOLDE = "solde", "Solde"
    ECHÉANCE_LOYER = "echéance_loyer", "Échéance de loyer"
    CAUTION = "caution", "Caution"



# ========== FINANCEMENT ==========
class FinancementStatus(models.TextChoices):
    JUSTIFICATIF_SOUMIS = "justificatif_soumis", "Justificatif soumis"
    ACCEPTE = "accepte", "Financement accepté"
    REFUSE = "refuse", "Financement rejeté"


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


# ==============================
# AUDIT: Catégories d'actions
# ==============================

class AuditActionCategory(models.TextChoices):
    """Catégories d'actions pour l'audit"""
    AUTHENTICATION = "authentication", "Authentification"
    AUTHORIZATION = "authorization", "Autorisation"
    DATA_CREATE = "data_create", "Création de données"
    DATA_READ = "data_read", "Lecture de données"
    DATA_UPDATE = "data_update", "Mise à jour de données"
    DATA_DELETE = "data_delete", "Suppression de données"
    BUSINESS_LOGIC = "business_logic", "Logique métier"
    FILE_UPLOAD = "file_upload", "Upload de fichier"
    FILE_DOWNLOAD = "file_download", "Téléchargement de fichier"
    PAYMENT = "payment", "Paiement"
    CONTRACT = "contract", "Contrat"
    RESERVATION = "reservation", "Réservation"
    FINANCING = "financing", "Financement"
    DOCUMENT = "document", "Document"
    USER_MANAGEMENT = "user_management", "Gestion utilisateur"
    SYSTEM = "system", "Système"


class AuditActionResult(models.TextChoices):
    """Résultat d'une action auditée"""
    SUCCESS = "success", "Succès"
    FAILURE = "failure", "Échec"
    PARTIAL = "partial", "Partiel"
    PENDING = "pending", "En attente"
