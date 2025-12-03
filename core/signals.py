"""
Signaux et audit logging automatiques pour les modèles critiques.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.utils import audit_log
from sales.models import Reservation, Contrat, Paiement, Financement, Echeance
from catalog.models import Programme, Unite


@receiver(post_save, sender=Reservation)
def audit_reservation_save(sender, instance, created, **kwargs):
    """Auditer la création/mise à jour de réservation."""
    action = "reservation_created" if created else "reservation_updated"
    payload = {
        "statut": instance.statut,
        "acompte": str(instance.acompte),
        "client_id": str(instance.client.id) if instance.client else None,
        "unite_id": str(instance.unite.id) if instance.unite else None,
    }
    # On ne peut pas accéder facilement au user/request ici, donc on laisse vide
    audit_log(None, instance, action, payload)


@receiver(post_save, sender=Contrat)
def audit_contrat_save(sender, instance, created, **kwargs):
    """Auditer la création/mise à jour de contrat."""
    action = "contrat_created" if created else "contrat_updated"
    payload = {
        "numero": instance.numero,
        "statut": instance.statut,
        "signe_le": str(instance.signe_le) if instance.signe_le else None,
    }
    audit_log(None, instance, action, payload)


@receiver(post_save, sender=Paiement)
def audit_paiement_save(sender, instance, created, **kwargs):
    """Auditer la création/mise à jour de paiement."""
    action = "paiement_created" if created else "paiement_updated"
    payload = {
        "montant": str(instance.montant),
        "statut": instance.statut,
        "moyen": instance.moyen,
    }
    audit_log(None, instance, action, payload)


@receiver(post_save, sender=Financement)
def audit_financement_save(sender, instance, created, **kwargs):
    """Auditer la création/mise à jour de financement."""
    action = "financement_created" if created else "financement_updated"
    payload = {
        "montant": str(instance.montant),
        "statut": instance.statut,
        "type": instance.type,
    }
    audit_log(None, instance, action, payload)
