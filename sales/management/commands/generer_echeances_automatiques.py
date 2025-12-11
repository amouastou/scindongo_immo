"""
Commande de management Django pour générer automatiquement les échéances mensuelles
quand un client n'a pas payé avant le 27 du mois.

Usage:
    python manage.py generer_echeances_automatiques

Cette commande doit être exécutée automatiquement chaque jour (via cron ou Celery Beat)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from sales.models import Reservation, EcheanceLoyer
from core.choices import PaiementStatus


class Command(BaseCommand):
    help = "Génère automatiquement les échéances mensuelles pour les locations (le 27 de chaque mois)"

    def handle(self, *args, **options):
        aujourd_hui = date.today()
        
        # Ne générer que le 27 de chaque mois
        if aujourd_hui.day != 27:
            self.stdout.write(
                self.style.WARNING(
                    f"⏭️  Pas le 27 du mois (aujourd'hui: {aujourd_hui}). Génération skippée."
                )
            )
            return
        
        self.stdout.write(self.style.SUCCESS(f"🗓️  Génération des échéances pour le {aujourd_hui}"))
        
        # Trouver toutes les réservations location avec caution validée
        reservations_location = Reservation.objects.filter(
            unite__programme__type_operation='location',
            paiements__type_paiement='caution',
            paiements__statut=PaiementStatus.VALIDE
        ).distinct()
        
        self.stdout.write(f"📊 {reservations_location.count()} réservations location trouvées")
        
        nb_echeances_generees = 0
        
        for reservation in reservations_location:
            # Trouver la dernière échéance créée
            derniere_echeance = reservation.echeances_loyer.order_by('-numero_mois').first()
            
            if not derniere_echeance:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Réservation {reservation.id}: Aucune échéance existante (caution validée?)"
                    )
                )
                continue
            
            # Si la dernière échéance n'est pas payée, générer la suivante
            if derniere_echeance.paiement is None:
                numero_suivant = derniere_echeance.numero_mois + 1
                
                # Vérifier qu'on n'a pas dépassé la durée du bail
                if numero_suivant > reservation.duree_bail_mois:
                    self.stdout.write(
                        f"✅ Réservation {reservation.id}: Bail terminé ({reservation.duree_bail_mois} mois)"
                    )
                    continue
                
                # Vérifier que l'échéance suivante n'existe pas déjà
                if reservation.echeances_loyer.filter(numero_mois=numero_suivant).exists():
                    continue
                
                # Calculer la date d'échéance suivante
                date_echeance_suivante = derniere_echeance.date_echeance + relativedelta(months=1)
                
                # Montant mensuel
                montant_mensuel = reservation.unite.modele_bien.prix_base_ttc
                
                # Créer l'échéance
                nouvelle_echeance = EcheanceLoyer.objects.create(
                    reservation=reservation,
                    numero_mois=numero_suivant,
                    montant=montant_mensuel,
                    date_echeance=date_echeance_suivante,
                    statut_paiement=PaiementStatus.ENREGISTRE
                )
                
                nb_echeances_generees += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Réservation {reservation.id} ({reservation.client}): "
                        f"Échéance {numero_suivant} créée (montant: {montant_mensuel} FCFA, "
                        f"date limite: {date_echeance_suivante})"
                    )
                )
        
        if nb_echeances_generees > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🎉 {nb_echeances_generees} nouvelle(s) échéance(s) générée(s) !"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✅ Aucune nouvelle échéance à générer aujourd'hui.")
            )
