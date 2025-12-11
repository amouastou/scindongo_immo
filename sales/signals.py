"""
Signaux pour SCINDONGO Immo - Logique métier automatisée.

- Génération automatique des échéances de loyer lors de validation de caution
- Mise à jour du statut des unités lors de confirmation/annulation réservation
- Logs d'audit sur les paiements critiques
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Paiement, Reservation, EcheanceLoyer
from core.choices import PaiementStatus, PaiementType, OperationType, UniteStatus
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Paiement)
def on_paiement_validated(sender, instance, created, **kwargs):
    """
    Quand un paiement CAUTION est validé pour une LOCATION,
    générer automatiquement les échéances mensuelles.
    
    Échéance Mois 1 doit être créée dès que la caution est validée.
    """
    paiement = instance
    
    # Seuls les paiements validés (changeant de statut)
    if paiement.statut != PaiementStatus.VALIDE:
        return
    
    # Seule la CAUTION déclenche la génération des échéances
    if paiement.type_paiement != PaiementType.CAUTION:
        return
    
    reservation = paiement.reservation
    
    # Vérifier que c'est une LOCATION
    if not reservation.is_location():
        return
    
    # Vérifier que les échéances n'existent pas déjà
    if reservation.echeances_loyer.exists():
        logger.info(f"Échéances existantes pour réservation {reservation.id}, pas de création")
        return
    
    # Générer les échéances
    try:
        from .utils import generer_echeances_loyer
        nb_created, nb_updated = generer_echeances_loyer(
            reservation,
            date.today()
        )
        logger.info(
            f"✅ Échéances générées pour réservation {reservation.id}: "
            f"{nb_created} créées, {nb_updated} mises à jour"
        )
    except Exception as e:
        logger.error(f"❌ Erreur génération échéances pour réservation {reservation.id}: {e}")


@receiver(post_save, sender=Reservation)
def on_reservation_status_changed(sender, instance, created, **kwargs):
    """
    Quand le statut d'une réservation change (confirmee),
    mettre à jour le statut de l'unité.
    """
    reservation = instance
    unite = reservation.unite
    
    # 1. Réservation CONFIRMÉE → Unité RESERVE (pour VENTE)
    if reservation.statut == 'confirmee' and reservation.is_vente():
        if unite.statut_disponibilite != UniteStatus.RESERVE:
            unite.statut_disponibilite = UniteStatus.RESERVE
            unite.save(update_fields=['statut_disponibilite'])
            logger.info(f"Unité {unite.reference_lot} marquée RESERVE (réservation confirmée)")
    
    # 2. Réservation CONFIRMÉE → Unité RESERVE (pour LOCATION)
    if reservation.statut == 'confirmee' and reservation.is_location():
        if unite.statut_disponibilite != UniteStatus.RESERVE:
            unite.statut_disponibilite = UniteStatus.RESERVE
            unite.save(update_fields=['statut_disponibilite'])
            logger.info(f"Unité {unite.reference_lot} marquée RESERVE (location confirmée)")
    
    # 3. Réservation ANNULÉE → Remettre unité DISPONIBLE
    if reservation.statut == 'annulee':
        if unite.statut_disponibilite != UniteStatus.DISPONIBLE:
            unite.statut_disponibilite = UniteStatus.DISPONIBLE
            unite.save(update_fields=['statut_disponibilite'])
            logger.info(f"Unité {unite.reference_lot} remise DISPONIBLE (réservation annulée)")
