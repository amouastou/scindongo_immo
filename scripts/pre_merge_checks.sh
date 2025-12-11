#!/usr/bin/env bash

# 🧪 Script de Vérification Pré-Merge - SCINDONGO Immo
# Exécutez: bash scripts/pre_merge_checks.sh

set -e

echo "🚀 Démarrage des vérifications pré-merge..."
echo "=============================================="

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Compteur d'erreurs
ERRORS=0

# =============================================================================
# 1. VÉRIFICATION SYNTAXE PYTHON
# =============================================================================
echo -e "\n${YELLOW}1️⃣  Vérification Syntaxe Python...${NC}"

if python3 -m py_compile sales/views.py 2>/dev/null; then
    echo -e "${GREEN}✓ sales/views.py OK${NC}"
else
    echo -e "${RED}✗ sales/views.py ERREUR${NC}"
    ERRORS=$((ERRORS+1))
fi

if python3 -m py_compile core/signals.py 2>/dev/null; then
    echo -e "${GREEN}✓ core/signals.py OK${NC}"
else
    echo -e "${RED}✗ core/signals.py ERREUR${NC}"
    ERRORS=$((ERRORS+1))
fi

# =============================================================================
# 2. VÉRIFICATION DJANGO CHECK
# =============================================================================
echo -e "\n${YELLOW}2️⃣  Vérification Configuration Django...${NC}"

if docker-compose exec -T web python manage.py check 2>/dev/null | grep -q "0 silenced"; then
    echo -e "${GREEN}✓ Django check OK${NC}"
else
    echo -e "${RED}✗ Django check ERREUR${NC}"
    ERRORS=$((ERRORS+1))
fi

# =============================================================================
# 3. VÉRIFICATION INTÉGRITÉ BASE DE DONNÉES
# =============================================================================
echo -e "\n${YELLOW}3️⃣  Vérification Intégrité Base de Données...${NC}"

# Check orphaned echances
ORPHANED=$(docker-compose exec -T db psql -U scindongo -d scindongo_immo -c \
    "SELECT COUNT(*) FROM sales_echeanceloyer WHERE paiement_id IS NOT NULL AND paiement_id NOT IN (SELECT id FROM sales_paiement);" \
    2>/dev/null | grep -oE '[0-9]+' | head -1)

if [ "$ORPHANED" -eq 0 ] 2>/dev/null; then
    echo -e "${GREEN}✓ Pas d'échéances orphelines${NC}"
else
    echo -e "${RED}✗ $ORPHANED échéances orphelines trouvées${NC}"
    ERRORS=$((ERRORS+1))
fi

# Check duplicate echances
DUPLICATES=$(docker-compose exec -T db psql -U scindongo -d scindongo_immo -c \
    "SELECT COUNT(*) FROM (SELECT reservation_id, numero_mois, COUNT(*) as cnt FROM sales_echeanceloyer GROUP BY reservation_id, numero_mois HAVING COUNT(*) > 1) t;" \
    2>/dev/null | grep -oE '[0-9]+' | head -1)

if [ "$DUPLICATES" -eq 0 ] 2>/dev/null; then
    echo -e "${GREEN}✓ Pas d'échéances dupliquées${NC}"
else
    echo -e "${RED}✗ $DUPLICATES échéances dupliquées trouvées${NC}"
    ERRORS=$((ERRORS+1))
fi

# =============================================================================
# 4. VÉRIFICATION MIGRATIONS
# =============================================================================
echo -e "\n${YELLOW}4️⃣  Vérification Migrations...${NC}"

PENDING=$(docker-compose exec -T web python manage.py makemigrations --dry-run 2>/dev/null | grep "No changes" || echo "HAS_CHANGES")

if [ "$PENDING" = "No changes detected" ] || [[ "$PENDING" == *"No changes"* ]]; then
    echo -e "${GREEN}✓ Aucune migration en attente${NC}"
else
    echo -e "${YELLOW}⚠ Migrations en attente${NC}"
fi

# =============================================================================
# 5. VÉRIFICATION PERMISSIONS FICHIERS
# =============================================================================
echo -e "\n${YELLOW}5️⃣  Vérification Permissions...${NC}"

if [ -r "sales/views.py" ] && [ -r "core/signals.py" ] && [ -r "TESTING_PLAN.md" ]; then
    echo -e "${GREEN}✓ Fichiers accessibles${NC}"
else
    echo -e "${RED}✗ Problème de permissions${NC}"
    ERRORS=$((ERRORS+1))
fi

# =============================================================================
# 6. VÉRIFICATION FICHIERS CLÉS
# =============================================================================
echo -e "\n${YELLOW}6️⃣  Vérification Fichiers Clés...${NC}"

REQUIRED_FILES=(
    "sales/views.py"
    "sales/models.py"
    "sales/urls.py"
    "core/signals.py"
    "templates/dashboards/commercial_dashboard.html"
    "templates/sales/commercial_search_unite.html"
    "TESTING_PLAN.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file MANQUANT${NC}"
        ERRORS=$((ERRORS+1))
    fi
done

# =============================================================================
# 7. RÉSUMÉ
# =============================================================================
echo -e "\n=============================================="
echo -e "${YELLOW}📋 RÉSUMÉ${NC}"
echo "=============================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ TOUS LES TESTS PASSENT - PRÊT POUR LA FUSION${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS ERREUR(S) DÉTECTÉE(S) - CORRIGER AVANT LA FUSION${NC}"
    exit 1
fi
