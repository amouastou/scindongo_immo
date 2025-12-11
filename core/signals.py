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


@receiver(post_save, sender=Paiement)
def generer_echeances_apres_caution_validee(sender, instance, created, **kwargs):
    """
    Générer la PREMIÈRE échéance de loyer quand la caution est validée.
    Les échéances suivantes seront générées au fur et à mesure.
    """
    from sales.models import EcheanceLoyer
    from core.choices import PaiementType
    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta
    
    # Vérifier que c'est un paiement de caution validé
    if instance.type_paiement != PaiementType.CAUTION or instance.statut != PaiementStatus.VALIDE:
        return
    
    # Vérifier que c'est une réservation location
    reservation = instance.reservation
    if not reservation.is_location():
        return
    
    # Vérifier que la première échéance n'existe pas déjà
    if reservation.echeances_loyer.filter(numero_mois=1).exists():
        return  # L'échéance 1 existe déjà
    
    try:
        # Calculer la date de début du bail = 1er jour du mois prochain
        aujourd_hui = date.today()
        prochain_mois = aujourd_hui.replace(day=1) + timedelta(days=32)
        date_debut_bail = prochain_mois.replace(day=1)
        
        # Date d'échéance = 10 du mois suivant le début du bail
        date_echeance_mois_1 = date_debut_bail + relativedelta(months=1)
        date_echeance_mois_1 = date_echeance_mois_1.replace(day=10)
        
        # Montant mensuel
        montant_mensuel = reservation.unite.prix_ttc
        
        # Créer SEULEMENT la première échéance
        echeance = EcheanceLoyer.objects.create(
            reservation=reservation,
            numero_mois=1,
            montant=montant_mensuel,
            date_echeance=date_echeance_mois_1,
            statut_paiement=PaiementStatus.ENREGISTRE
        )
        
        print(f"✅ Première échéance générée pour réservation {reservation.id}: {date_echeance_mois_1}")
    except Exception as e:
        print(f"❌ Erreur génération première échéance: {e}")


@receiver(post_save, sender=Paiement)
def generer_echeance_suivante_apres_paiement(sender, instance, created, **kwargs):
    """
    Générer l'échéance suivante quand une échéance de loyer est payée et validée.
    """
    from sales.models import EcheanceLoyer
    from core.choices import PaiementType
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    # Vérifier que c'est un paiement d'échéance validé
    if instance.type_paiement != PaiementType.ECHÉANCE_LOYER or instance.statut != PaiementStatus.VALIDE:
        return
    
    # Récupérer l'échéance associée à ce paiement
    try:
        echeance_payee = EcheanceLoyer.objects.get(paiement=instance)
    except EcheanceLoyer.DoesNotExist:
        return
    
    reservation = echeance_payee.reservation
    numero_suivant = echeance_payee.numero_mois + 1
    
    # Vérifier qu'on n'a pas dépassé la durée du bail
    if numero_suivant > reservation.duree_bail_mois:
        print(f"✅ Toutes les échéances du bail ont été générées")
        return
    
    # Vérifier que l'échéance suivante n'existe pas déjà
    if reservation.echeances_loyer.filter(numero_mois=numero_suivant).exists():
        return
    
    try:
        # Calculer la date d'échéance suivante = date de l'échéance payée + 1 mois
        date_echeance_suivante = echeance_payee.date_echeance + relativedelta(months=1)
        
        # Montant mensuel
        montant_mensuel = reservation.unite.prix_ttc
        
        # Créer l'échéance suivante
        nouvelle_echeance = EcheanceLoyer.objects.create(
            reservation=reservation,
            numero_mois=numero_suivant,
            montant=montant_mensuel,
            date_echeance=date_echeance_suivante,
            statut_paiement=PaiementStatus.ENREGISTRE
        )
        
        print(f"✅ Échéance {numero_suivant} générée après paiement de l'échéance {echeance_payee.numero_mois}")
    except Exception as e:
        print(f"❌ Erreur génération échéance suivante: {e}")


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
