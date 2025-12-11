#!/usr/bin/env bash

# 🧹 Script de Nettoyage Base de Données - SCINDONGO Immo
# Avant de merger, nettoyer les données de test

echo "🧹 Nettoyage Base de Données..."

# Supprimer les échéances orphelines
echo "Suppression des échéances orphelines..."
docker-compose exec -T db psql -U scindongo -d scindongo_immo -c \
    "DELETE FROM sales_echeanceloyer WHERE paiement_id IS NOT NULL AND paiement_id NOT IN (SELECT id FROM sales_paiement);"

# Supprimer les échéances dupliquées (garder la première)
echo "Suppression des échéances dupliquées..."
docker-compose exec -T db psql -U scindongo -d scindongo_immo -c \
    "DELETE FROM sales_echeanceloyer WHERE id NOT IN (
        SELECT MIN(id) FROM sales_echeanceloyer GROUP BY reservation_id, numero_mois
    ) AND (SELECT COUNT(*) FROM sales_echeanceloyer e2 WHERE e2.reservation_id = sales_echeanceloyer.reservation_id AND e2.numero_mois = sales_echeanceloyer.numero_mois) > 1;"

# Vérifier l'intégrité
echo "Vérification..."
echo "Échéances orphelines:"
docker-compose exec -T db psql -U scindongo -d scindongo_immo -c \
    "SELECT COUNT(*) FROM sales_echeanceloyer WHERE paiement_id IS NOT NULL AND paiement_id NOT IN (SELECT id FROM sales_paiement);"

echo "Échéances dupliquées:"
docker-compose exec -T db psql -U scindongo -d scindongo_immo -c \
    "SELECT COUNT(*) FROM (SELECT reservation_id, numero_mois, COUNT(*) as cnt FROM sales_echeanceloyer GROUP BY reservation_id, numero_mois HAVING COUNT(*) > 1) t;"

echo "✅ Nettoyage terminé"
