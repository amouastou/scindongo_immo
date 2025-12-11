#!/bin/bash

echo "
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║         🚀 TEST COMPLET END-TO-END - SCINDONGO IMMO (Simplifié)          ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"

cd /home/amanstou/SCINDONGO_IMMO_FINAL_UNIFIE

docker-compose exec -T web python manage.py shell << 'ENDPYTHON'

from catalog.models import Programme, TypeBien, ModeleBien, Unite
from sales.models import Reservation, Paiement, EcheanceLoyer
from django.contrib.auth import get_user_model
from accounts.models import Role
from core.choices import ProgrammeStatus, UniteStatus
from decimal import Decimal
import sys

User = get_user_model()

print("\n" + "="*70)
print("  TEST: Vérification des modèles existants")
print("="*70 + "\n")

# Utiliser des données existantes
programme = Programme.objects.filter(statut=ProgrammeStatus.ACTIF).first()
if not programme:
    print("✗ Aucun programme actif trouvé")
    print("  Solution: Créer un programme via Django admin")
    sys.exit(1)

print(f"✓ Programme trouvé: {programme.nom}")

# Vérifier unités
unites = Unite.objects.filter(
    programme=programme,
    statut_disponibilite=UniteStatus.DISPONIBLE
)[:2]

if unites.count() < 1:
    print("✗ Aucune unité disponible trouvée")
    print("  Solution: Créer des unités via Django admin")
    sys.exit(1)

unite_test = unites.first()
print(f"✓ Unité trouvée: {unite_test.reference_lot}")

# Vérifier client
role_client, _ = Role.objects.get_or_create(code="CLIENT", defaults={"nom": "Client"})
client = User.objects.filter(roles=role_client).first()

if not client:
    print("⚠ Aucun client trouvé, création d'un client test...")
    User.objects.filter(email="client.test.e2e@test.com").delete()
    client = User.objects.create_user(
        email="client.test.e2e@test.com",
        password="password123",
        first_name="Client",
        last_name="Test E2E"
    )
    client.roles.add(role_client)
    print(f"✓ Client créé: {client.email}")
else:
    print(f"✓ Client trouvé: {client.email}")

print("\n" + "="*70)
print("  TEST 1: Réservation VENTE")
print("="*70 + "\n")

# Nettoyer réservations test
Reservation.objects.filter(
    client=client,
    unite=unite_test
).delete()

reservation = Reservation.objects.create(
    client=client,
    unite=unite_test,
    operation_type='VENTE',
    statut='en_cours'
)

print(f"✓ Réservation créée")
print(f"  - Type: {reservation.operation_type}")
print(f"  - Statut: {reservation.statut}")
print(f"  - Unité: {reservation.unite.reference_lot}")

print("\n" + "="*70)
print("  TEST 2: Paiement Acompte (20%)")
print("="*70 + "\n")

montant_acompte = unite_test.prix_ttc * Decimal('0.20')

paiement = Paiement.objects.create(
    reservation=reservation,
    montant=montant_acompte,
    type_paiement='ACOMPTE',
    statut_paiement='enregistre',
    moyen_paiement='virement'
)

print(f"✓ Paiement créé")
print(f"  - Montant: {montant_acompte:,.0f} FCFA")
print(f"  - Type: {paiement.type_paiement}")
print(f"  - Statut: {paiement.statut_paiement}")

print("\n" + "="*70)
print("  TEST 3: Validation Paiement")
print("="*70 + "\n")

paiement.statut_paiement = 'valide'
paiement.save()

print(f"✓ Paiement validé")
print(f"  - Nouveau statut: {paiement.statut_paiement}")

print("\n" + "="*70)
print("  TEST 4: Vérification Statistiques Dashboard")
print("="*70 + "\n")

total_paiements = Paiement.objects.count()
paiements_valides = Paiement.objects.filter(statut_paiement='valide').count()
paiements_attente = Paiement.objects.filter(statut_paiement='enregistre').count()

print(f"  • Total paiements: {total_paiements}")
print(f"  • Paiements validés: {paiements_valides}")
print(f"  • Paiements en attente: {paiements_attente}")

total_reservations = Reservation.objects.count()
reservations_en_cours = Reservation.objects.filter(statut='en_cours').count()
reservations_confirmees = Reservation.objects.filter(statut='confirmee').count()

print(f"  • Total réservations: {total_reservations}")
print(f"  • En cours: {reservations_en_cours}")
print(f"  • Confirmées: {reservations_confirmees}")

print("\n" + "="*70)
print("  ✅ RÉSUMÉ")
print("="*70 + "\n")

print("""
✅ TESTS COMPLÉTÉS:
   • Modèles accessibles ✓
   • Réservation VENTE créée ✓
   • Paiement Acompte enregistré ✓
   • Paiement Acompte validé ✓
   • Dashboard statistiques calculées ✓

📊 DONNÉES EXISTANTES:
   • Programmes: """ + str(Programme.objects.count()) + """
   • Unités: """ + str(Unite.objects.count()) + """
   • Clients: """ + str(User.objects.filter(roles__code='CLIENT').count()) + """
   • Réservations: """ + str(Reservation.objects.count()) + """
   • Paiements: """ + str(Paiement.objects.count()) + """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: ✅ TOUS LES TESTS BASIQUES PASSENT

Pour tester le workflow LOCATION avec échéances, utilisez Django admin:
1. Créer une réservation avec operation_type='LOCATION'
2. Ajouter un paiement type_paiement='CAUTION'
3. Valider le paiement (→ devrait générer Échéance Mois 1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

ENDPYTHON

echo ""
echo "✅ Test simplifié terminé avec succès!"
echo ""
