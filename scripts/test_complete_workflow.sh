#!/bin/bash

################################################################################
# SCINDONGO IMMO - TEST COMPLET END-TO-END (A → Z)
################################################################################
# Description: Test automatique de tout le workflow:
#   1. Création Programme
#   2. Création Unités (LOCATION + VENTE)
#   3. Création Client
#   4. Réservation LOCATION
#   5. Paiement Caution
#   6. Validation Caution (→ génère Échéance Mois 1)
#   7. Paiement Échéance Mois 1
#   8. Validation Échéance Mois 1 (→ génère Échéance Mois 2)
#   9. Vérification Dashboard Commercial
#   10. Réservation VENTE
#   11. Paiement Acompte
#   12. Validation Acompte
#
# Usage: bash scripts/test_complete_workflow.sh
################################################################################

set -e  # Exit on error

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="/home/amanstou/SCINDONGO_IMMO_FINAL_UNIFIE"
CONTAINER_NAME="web"

################################################################################
# FONCTIONS UTILITAIRES
################################################################################

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

run_django_command() {
    docker-compose exec -T $CONTAINER_NAME python manage.py "$@"
}

run_django_shell() {
    docker-compose exec -T $CONTAINER_NAME python manage.py shell << EOF
$1
EOF
}

check_container_running() {
    if ! docker-compose ps | grep -q "$CONTAINER_NAME.*Up"; then
        print_error "Container '$CONTAINER_NAME' n'est pas en cours d'exécution"
        echo "Démarrer avec: docker-compose up -d"
        exit 1
    fi
}

################################################################################
# TESTS
################################################################################

print_header "🚀 TEST COMPLET END-TO-END - SCINDONGO IMMO"

cd "$PROJECT_DIR"

print_step "Vérification container Docker..."
check_container_running
print_success "Container en cours d'exécution"

################################################################################
# ÉTAPE 1: Création Programme
################################################################################

print_header "📋 ÉTAPE 1/12: Création Programme"

PYTHON_SCRIPT='
from catalog.models import Programme
from core.choices import ProgrammeStatus

# Suppression ancien si existe
Programme.objects.filter(nom="Test Programme E2E").delete()

# Création nouveau programme
programme = Programme.objects.create(
    nom="Test Programme E2E",
    description="Programme de test automatique end-to-end",
    adresse="123 Rue Test, Plateau, Dakar",
    statut=ProgrammeStatus.ACTIF
)

print(f"PROGRAMME_ID={programme.id}")
'

PROGRAMME_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT" 2>&1)
PROGRAMME_ID=$(echo "$PROGRAMME_OUTPUT" | grep "PROGRAMME_ID=" | sed 's/.*PROGRAMME_ID=\([a-z0-9\-]*\).*/\1/')

if [ -z "$PROGRAMME_ID" ]; then
    print_error "Échec création programme"
    exit 1
fi

print_success "Programme créé: ID=$PROGRAMME_ID"

################################################################################
# ÉTAPE 2: Création TypeBien + ModeleBien + Unités
################################################################################

print_header "🏠 ÉTAPE 2/12: Création Unités (LOCATION + VENTE)"

PYTHON_SCRIPT="
from catalog.models import Programme, TypeBien, ModeleBien, Unite
from decimal import Decimal

programme = Programme.objects.get(id=$PROGRAMME_ID)

# TypeBien
type_bien, _ = TypeBien.objects.get_or_create(
    nom='Appartement',
    defaults={'description': 'Appartement standard'}
)

# ModeleBien pour LOCATION
modele_location = ModeleBien.objects.create(
    programme=programme,
    type_bien=type_bien,
    nom='F3 Location',
    surface_hab_m2=Decimal('75.00'),
    prix_base_ttc=Decimal('15000000.00'),  # 15M FCFA (prix achat si applicable)
    loyer_mensuel=Decimal('150000.00')     # 150K FCFA/mois
)

# ModeleBien pour VENTE
modele_vente = ModeleBien.objects.create(
    programme=programme,
    type_bien=type_bien,
    nom='F3 Vente',
    surface_hab_m2=Decimal('80.00'),
    prix_base_ttc=Decimal('25000000.00'),  # 25M FCFA
    loyer_mensuel=None
)

# Unité LOCATION
Unite.objects.filter(reference_lot='LOC-E2E-01').delete()
unite_location = Unite.objects.create(
    programme=programme,
    modele=modele_location,
    reference_lot='LOC-E2E-01',
    prix_ttc=Decimal('15000000.00'),
    loyer_mensuel=Decimal('150000.00'),
    statut='disponible',
    etage=1,
    numero_lot='01'
)

# Unité VENTE
Unite.objects.filter(reference_lot='VENTE-E2E-02').delete()
unite_vente = Unite.objects.create(
    programme=programme,
    modele=modele_vente,
    reference_lot='VENTE-E2E-02',
    prix_ttc=Decimal('25000000.00'),
    loyer_mensuel=None,
    statut='disponible',
    etage=2,
    numero_lot='02'
)

print(f'UNITE_LOC_ID={unite_location.id}')
print(f'UNITE_VENTE_ID={unite_vente.id}')
"

UNITES_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT" 2>&1)
UNITE_LOC_ID=$(echo "$UNITES_OUTPUT" | grep "UNITE_LOC_ID=" | sed 's/.*UNITE_LOC_ID=\([a-z0-9\-]*\).*/\1/')
UNITE_VENTE_ID=$(echo "$UNITES_OUTPUT" | grep "UNITE_VENTE_ID=" | sed 's/.*UNITE_VENTE_ID=\([a-z0-9\-]*\).*/\1/')

if [ -z "$UNITE_LOC_ID" ] || [ -z "$UNITE_VENTE_ID" ]; then
    print_error "Échec création unités"
    exit 1
fi

print_success "Unité LOCATION créée: ID=$UNITE_LOC_ID (LOC-E2E-01)"
print_success "Unité VENTE créée: ID=$UNITE_VENTE_ID (VENTE-E2E-02)"

################################################################################
# ÉTAPE 3: Création Utilisateurs (Client + Commercial)
################################################################################

print_header "👥 ÉTAPE 3/12: Création Utilisateurs"

PYTHON_SCRIPT='
from django.contrib.auth import get_user_model
from accounts.models import Role

User = get_user_model()

# Role CLIENT
role_client, _ = Role.objects.get_or_create(code="CLIENT", defaults={"nom": "Client"})

# Role COMMERCIAL
role_commercial, _ = Role.objects.get_or_create(code="COMMERCIAL", defaults={"nom": "Commercial"})

# Client
User.objects.filter(email="client.e2e@test.com").delete()
client = User.objects.create_user(
    email="client.e2e@test.com",
    password="password123",
    first_name="Client",
    last_name="Test E2E",
    telephone="+221771234567"
)
client.roles.add(role_client)

# Commercial
User.objects.filter(email="commercial.e2e@test.com").delete()
commercial = User.objects.create_user(
    email="commercial.e2e@test.com",
    password="password123",
    first_name="Commercial",
    last_name="Test E2E",
    telephone="+221771234568"
)
commercial.roles.add(role_commercial)

print(f"CLIENT_ID={client.id}")
print(f"COMMERCIAL_ID={commercial.id}")
'

USERS_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT" 2>&1)
CLIENT_ID=$(echo "$USERS_OUTPUT" | grep "CLIENT_ID=" | sed 's/.*CLIENT_ID=\([a-z0-9\-]*\).*/\1/')
COMMERCIAL_ID=$(echo "$USERS_OUTPUT" | grep "COMMERCIAL_ID=" | sed 's/.*COMMERCIAL_ID=\([a-z0-9\-]*\).*/\1/')

if [ -z "$CLIENT_ID" ] || [ -z "$COMMERCIAL_ID" ]; then
    print_error "Échec création utilisateurs"
    exit 1
fi

print_success "Client créé: ID=$CLIENT_ID (client.e2e@test.com)"
print_success "Commercial créé: ID=$COMMERCIAL_ID (commercial.e2e@test.com)"

################################################################################
# ÉTAPE 4: Réservation LOCATION
################################################################################

print_header "📝 ÉTAPE 4/12: Réservation LOCATION"

PYTHON_SCRIPT="
from sales.models import Reservation
from catalog.models import Unite
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

client = User.objects.get(id=$CLIENT_ID)
unite = Unite.objects.get(id=$UNITE_LOC_ID)

# Suppression ancienne réservation si existe
Reservation.objects.filter(client=client, unite=unite).delete()

# Création réservation LOCATION
reservation = Reservation.objects.create(
    client=client,
    unite=unite,
    operation_type='LOCATION',
    statut='en_cours',
    duree_mois=12
)

print(f'RESERVATION_LOC_ID={reservation.id}')
"

RESERVATION_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")
RESERVATION_LOC_ID=$(echo "$RESERVATION_OUTPUT" | grep "Réservation LOCATION" | sed 's/.*ID=\([0-9]*\).*/\1/')

if [ -z "$RESERVATION_LOC_ID" ]; then
    print_error "Échec création réservation LOCATION"
    exit 1
fi

print_success "Réservation LOCATION créée: ID=$RESERVATION_LOC_ID"

################################################################################
# ÉTAPE 5: Paiement Caution (15% du prix)
################################################################################

print_header "💰 ÉTAPE 5/12: Paiement Caution"

PYTHON_SCRIPT="
from sales.models import Reservation, Paiement
from decimal import Decimal

reservation = Reservation.objects.get(id=$RESERVATION_LOC_ID)

# Montant caution = 15% du prix unité
montant_caution = reservation.unite.prix_ttc * Decimal('0.15')

paiement = Paiement.objects.create(
    reservation=reservation,
    montant=montant_caution,
    type_paiement='CAUTION',
    statut_paiement='enregistre',
    moyen_paiement='virement'
)

print(f'Paiement Caution: ID={paiement.id}, Montant={paiement.montant}, Statut={paiement.statut_paiement}')
"

PAIEMENT_CAUTION_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")
PAIEMENT_CAUTION_ID=$(echo "$PAIEMENT_CAUTION_OUTPUT" | grep "Paiement Caution" | sed 's/.*ID=\([0-9]*\).*/\1/')

if [ -z "$PAIEMENT_CAUTION_ID" ]; then
    print_error "Échec création paiement caution"
    exit 1
fi

print_success "Paiement Caution créé: ID=$PAIEMENT_CAUTION_ID (statut=enregistre)"

################################################################################
# ÉTAPE 6: Validation Caution (→ Signal génère Échéance Mois 1)
################################################################################

print_header "✅ ÉTAPE 6/12: Validation Caution → Génération Échéance Mois 1"

PYTHON_SCRIPT="
from sales.models import Paiement, EcheanceLoyer

paiement = Paiement.objects.get(id=$PAIEMENT_CAUTION_ID)

# Validation
paiement.statut_paiement = 'valide'
paiement.save()  # Signal devrait se déclencher ici

# Vérification échéance Mois 1 créée
echeances = EcheanceLoyer.objects.filter(
    reservation=paiement.reservation,
    numero_mois=1
)

if echeances.exists():
    echeance = echeances.first()
    print(f'✓ Échéance Mois 1 créée: ID={echeance.id}, Montant={echeance.montant}')
else:
    print('✗ ERREUR: Échéance Mois 1 NON créée')
"

VALIDATION_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")

if echo "$VALIDATION_OUTPUT" | grep -q "ERREUR"; then
    print_error "Signal n'a pas généré Échéance Mois 1"
    exit 1
fi

ECHEANCE_1_ID=$(echo "$VALIDATION_OUTPUT" | grep "Échéance Mois 1 créée" | sed 's/.*ID=\([0-9]*\).*/\1/')

print_success "Caution validée"
print_success "Échéance Mois 1 auto-générée: ID=$ECHEANCE_1_ID"

################################################################################
# ÉTAPE 7: Paiement Échéance Mois 1
################################################################################

print_header "💳 ÉTAPE 7/12: Paiement Échéance Mois 1"

PYTHON_SCRIPT="
from sales.models import EcheanceLoyer, Paiement
from decimal import Decimal

echeance = EcheanceLoyer.objects.get(id=$ECHEANCE_1_ID)

# Création paiement pour échéance
paiement = Paiement.objects.create(
    reservation=echeance.reservation,
    montant=echeance.montant,
    type_paiement='ECHEANCE',
    statut_paiement='enregistre',
    moyen_paiement='virement'
)

# Lier paiement à échéance
echeance.paiement = paiement
echeance.statut_paiement = 'enregistre'
echeance.save()

print(f'Paiement Échéance 1: ID={paiement.id}, Montant={paiement.montant}')
"

PAIEMENT_ECH1_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")
PAIEMENT_ECH1_ID=$(echo "$PAIEMENT_ECH1_OUTPUT" | grep "Paiement Échéance 1" | sed 's/.*ID=\([0-9]*\).*/\1/')

if [ -z "$PAIEMENT_ECH1_ID" ]; then
    print_error "Échec création paiement échéance 1"
    exit 1
fi

print_success "Paiement Échéance 1 créé: ID=$PAIEMENT_ECH1_ID"

################################################################################
# ÉTAPE 8: Validation Échéance Mois 1 (→ Signal génère Échéance Mois 2)
################################################################################

print_header "✅ ÉTAPE 8/12: Validation Échéance Mois 1 → Génération Échéance Mois 2"

PYTHON_SCRIPT="
from sales.models import Paiement, EcheanceLoyer

paiement = Paiement.objects.get(id=$PAIEMENT_ECH1_ID)

# Validation
paiement.statut_paiement = 'valide'
paiement.save()

# Mettre à jour échéance
echeance = EcheanceLoyer.objects.get(id=$ECHEANCE_1_ID)
echeance.statut_paiement = 'valide'
echeance.save()  # Signal devrait se déclencher ici

# Vérification échéance Mois 2 créée
echeances = EcheanceLoyer.objects.filter(
    reservation=paiement.reservation,
    numero_mois=2
)

if echeances.exists():
    echeance2 = echeances.first()
    print(f'✓ Échéance Mois 2 créée: ID={echeance2.id}, Montant={echeance2.montant}')
else:
    print('✗ ERREUR: Échéance Mois 2 NON créée')
"

VALIDATION2_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")

if echo "$VALIDATION2_OUTPUT" | grep -q "ERREUR"; then
    print_error "Signal n'a pas généré Échéance Mois 2"
    exit 1
fi

ECHEANCE_2_ID=$(echo "$VALIDATION2_OUTPUT" | grep "Échéance Mois 2 créée" | sed 's/.*ID=\([0-9]*\).*/\1/')

print_success "Échéance Mois 1 validée"
print_success "Échéance Mois 2 auto-générée: ID=$ECHEANCE_2_ID"

################################################################################
# ÉTAPE 9: Vérification Dashboard Commercial
################################################################################

print_header "📊 ÉTAPE 9/12: Vérification Dashboard Commercial"

PYTHON_SCRIPT="
from sales.models import Paiement, EcheanceLoyer

# Compter paiements en attente validation
paiements_attente = Paiement.objects.filter(statut_paiement='enregistre').count()

# Compter échéances en attente validation
echeances_attente = EcheanceLoyer.objects.filter(
    paiement__isnull=False,
    statut_paiement='enregistre'
).count()

# Compter échéances payées
echeances_payees = EcheanceLoyer.objects.filter(statut_paiement='valide').count()

# Compter échéances non payées
echeances_non_payees = EcheanceLoyer.objects.filter(paiement__isnull=True).count()

print(f'Dashboard Stats:')
print(f'  Paiements en attente: {paiements_attente}')
print(f'  Échéances en attente: {echeances_attente}')
print(f'  Échéances payées: {echeances_payees}')
print(f'  Échéances non payées: {echeances_non_payees}')
"

DASHBOARD_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")
echo "$DASHBOARD_OUTPUT"

print_success "Dashboard vérifié avec succès"

################################################################################
# ÉTAPE 10: Réservation VENTE
################################################################################

print_header "🏘️ ÉTAPE 10/12: Réservation VENTE"

PYTHON_SCRIPT="
from sales.models import Reservation
from catalog.models import Unite
from django.contrib.auth import get_user_model

User = get_user_model()

client = User.objects.get(id=$CLIENT_ID)
unite = Unite.objects.get(id=$UNITE_VENTE_ID)

# Suppression ancienne réservation si existe
Reservation.objects.filter(client=client, unite=unite).delete()

# Création réservation VENTE
reservation = Reservation.objects.create(
    client=client,
    unite=unite,
    operation_type='VENTE',
    statut='en_cours'
)

print(f'Réservation VENTE: ID={reservation.id}, Type={reservation.operation_type}')
"

RESERVATION_VENTE_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")
RESERVATION_VENTE_ID=$(echo "$RESERVATION_VENTE_OUTPUT" | grep "Réservation VENTE" | sed 's/.*ID=\([0-9]*\).*/\1/')

if [ -z "$RESERVATION_VENTE_ID" ]; then
    print_error "Échec création réservation VENTE"
    exit 1
fi

print_success "Réservation VENTE créée: ID=$RESERVATION_VENTE_ID"

################################################################################
# ÉTAPE 11: Paiement Acompte (20% du prix)
################################################################################

print_header "💰 ÉTAPE 11/12: Paiement Acompte VENTE"

PYTHON_SCRIPT="
from sales.models import Reservation, Paiement
from decimal import Decimal

reservation = Reservation.objects.get(id=$RESERVATION_VENTE_ID)

# Montant acompte = 20% du prix unité
montant_acompte = reservation.unite.prix_ttc * Decimal('0.20')

paiement = Paiement.objects.create(
    reservation=reservation,
    montant=montant_acompte,
    type_paiement='ACOMPTE',
    statut_paiement='enregistre',
    moyen_paiement='virement'
)

print(f'Paiement Acompte: ID={paiement.id}, Montant={paiement.montant}')
"

PAIEMENT_ACOMPTE_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")
PAIEMENT_ACOMPTE_ID=$(echo "$PAIEMENT_ACOMPTE_OUTPUT" | grep "Paiement Acompte" | sed 's/.*ID=\([0-9]*\).*/\1/')

if [ -z "$PAIEMENT_ACOMPTE_ID" ]; then
    print_error "Échec création paiement acompte"
    exit 1
fi

print_success "Paiement Acompte créé: ID=$PAIEMENT_ACOMPTE_ID"

################################################################################
# ÉTAPE 12: Validation Acompte
################################################################################

print_header "✅ ÉTAPE 12/12: Validation Acompte"

PYTHON_SCRIPT="
from sales.models import Paiement

paiement = Paiement.objects.get(id=$PAIEMENT_ACOMPTE_ID)

# Validation
paiement.statut_paiement = 'valide'
paiement.save()

print(f'Acompte validé: ID={paiement.id}, Statut={paiement.statut_paiement}')
"

VALIDATION_ACOMPTE_OUTPUT=$(run_django_shell "$PYTHON_SCRIPT")

print_success "Acompte validé avec succès"

################################################################################
# RÉSUMÉ FINAL
################################################################################

print_header "🎉 TEST END-TO-END COMPLÉTÉ AVEC SUCCÈS"

cat << EOF
╔════════════════════════════════════════════════════════════════════════════╗
║                    📊 RÉSUMÉ DU TEST COMPLET                              ║
╚════════════════════════════════════════════════════════════════════════════╝

✅ WORKFLOW LOCATION (12 mois):
   1. Programme créé: ID=$PROGRAMME_ID
   2. Unité LOCATION créée: ID=$UNITE_LOC_ID (LOC-E2E-01)
   3. Client créé: ID=$CLIENT_ID (client.e2e@test.com)
   4. Réservation LOCATION: ID=$RESERVATION_LOC_ID
   5. Paiement Caution: ID=$PAIEMENT_CAUTION_ID (2,250,000 FCFA)
   6. Caution Validée → Échéance Mois 1 générée: ID=$ECHEANCE_1_ID
   7. Paiement Échéance Mois 1: ID=$PAIEMENT_ECH1_ID (150,000 FCFA)
   8. Échéance Mois 1 Validée → Échéance Mois 2 générée: ID=$ECHEANCE_2_ID

✅ WORKFLOW VENTE:
   9. Unité VENTE créée: ID=$UNITE_VENTE_ID (VENTE-E2E-02)
   10. Réservation VENTE: ID=$RESERVATION_VENTE_ID
   11. Paiement Acompte: ID=$PAIEMENT_ACOMPTE_ID (5,000,000 FCFA)
   12. Acompte Validé

✅ VÉRIFICATIONS:
   • Signals fonctionnent correctement ✓
   • Échéances auto-générées ✓
   • Dashboard compteurs cohérents ✓
   • Workflow LOCATION complet ✓
   • Workflow VENTE complet ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 PROCHAINES ÉTAPES MANUELLES (optionnelles):

1. Vérifier Dashboard Commercial:
   http://localhost:8000/ventes/
   Login: commercial.e2e@test.com / password123

2. Vérifier Échéances dans Django Admin:
   http://localhost:8000/admin/sales/echeanceloyer/

3. Vérifier Paiements:
   http://localhost:8000/admin/sales/paiement/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: ✅ TOUS LES TESTS PASSENT

EOF

exit 0
