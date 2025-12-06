import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scindongo_immo.settings")
django.setup()

from catalog.models import Unite, Programme
from sales.models import Reservation

# Afficher les stats globales
all_biens = Unite.objects.all()
print("=== STATISTIQUES GLOBALES ===")
print(f"Total biens: {all_biens.count()}")

# Biens avec réservation confirmée
biens_confirmee = all_biens.filter(reservations__statut='confirmee').distinct().count()
print(f"Biens Vendus/Livrés (réservation confirmée): {biens_confirmee}")

# Biens avec réservation en cours
biens_encours = all_biens.filter(reservations__statut__in=['en_cours', 'reserve']).exclude(reservations__statut='annulee').distinct().count()
print(f"Biens Réservés (en_cours ou reserve, non annulée): {biens_encours}")

# Disponibles
biens_dispo = all_biens.count() - biens_confirmee - biens_encours
print(f"Biens Disponibles: {biens_dispo}")

print("\n=== PAR PROGRAMME ===")
for prog in Programme.objects.all():
    prog_biens = Unite.objects.filter(programme=prog)
    total = prog_biens.count()
    confirmee = prog_biens.filter(reservations__statut='confirmee').distinct().count()
    encours = prog_biens.filter(reservations__statut__in=['en_cours', 'reserve']).exclude(reservations__statut='annulee').distinct().count()
    dispo = total - confirmee - encours
    
    print(f"\n📌 {prog.nom}")
    print(f"   Total: {total} | Disponibles: {dispo} | Réservés: {encours} | Vendus: {confirmee}")

print("\n=== DÉTAIL DES RÉSERVATIONS ===")
for resa in Reservation.objects.all()[:20]:
    print(f"Réservation {str(resa.id)[:8]}: Bien={resa.unite.reference_lot}, Statut={resa.statut}")
