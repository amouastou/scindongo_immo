"""
Signaux et audit logging automatiques pour les modèles critiques.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.utils import audit_log
from sales.models import Reservation, Contrat, Paiement, Financement, Echeance
from catalog.models import Programme, Unite
from core.choices import ReservationStatus, ContratStatus, PaiementStatus, FinancementStatus, UniteStatus


@receiver(post_save, sender=Reservation)
def cascade_reservation_cancellation(sender, instance, created, **kwargs):
    """
    Gérer la cascade lors de l'annulation d'une réservation :
    - Libérer l'unité
    - Marquer paiements comme annulés
    - Annuler contrat et financement (sauf s'ils sont déjà signés/acceptés)
    """
    # Ne traiter que les annulations (transition vers annulee)
    if instance.statut != ReservationStatus.ANNULEE:
        return
    
    # Ne traiter qu'une fois (éviter les boucles de signal)
    if instance.annulee_le is None:
        return
    
    # Libérer l'unité (la rendre disponible)
    if instance.unite.statut_disponibilite != UniteStatus.DISPONIBLE:
        instance.unite.statut_disponibilite = UniteStatus.DISPONIBLE
        instance.unite.save(update_fields=['statut_disponibilite'])
    
    # Annuler tous les paiements liés (sauf s'ils sont déjà validés)
    for paiement in instance.paiements.all():
        if paiement.statut != PaiementStatus.VALIDE:
            paiement.statut = PaiementStatus.REJETE
            paiement.save(update_fields=['statut'])
    
    # Annuler le contrat s'il existe et n'est pas signé
    if hasattr(instance, 'contrat'):
        if instance.contrat.statut != ContratStatus.SIGNE:
            instance.contrat.statut = ContratStatus.ANNULE
            instance.contrat.save(update_fields=['statut'])
    
    # Annuler le financement s'il existe et n'est pas accepté/clos
    if hasattr(instance, 'financement'):
        if instance.financement.statut not in [FinancementStatus.ACCEPTE, FinancementStatus.CLOS]:
            instance.financement.statut = FinancementStatus.ANNULE
            instance.financement.save(update_fields=['statut'])


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
