# 🧪 TEST COMPLET END-TO-END - Guide d'Utilisation

## 📋 Description

Ce script **`test_complete_workflow.sh`** effectue un test automatique complet du workflow SCINDONGO Immo de A à Z :

### Workflow LOCATION (Étapes 1-8):
1. ✅ Création Programme immobilier
2. ✅ Création Unité LOCATION (avec loyer mensuel)
3. ✅ Création Client
4. ✅ Réservation LOCATION (12 mois)
5. ✅ Paiement Caution (15% du prix)
6. ✅ **Validation Caution** → Signal génère **Échéance Mois 1**
7. ✅ Paiement Échéance Mois 1
8. ✅ **Validation Échéance Mois 1** → Signal génère **Échéance Mois 2**

### Workflow VENTE (Étapes 9-12):
9. ✅ Création Unité VENTE
10. ✅ Réservation VENTE
11. ✅ Paiement Acompte (20% du prix)
12. ✅ Validation Acompte

---

## 🚀 Comment Lancer le Test

### Prérequis
```bash
# 1. Container Docker doit être en cours d'exécution
docker-compose up -d

# 2. Vérifier que le container "web" est actif
docker-compose ps
```

### Lancer le Test Complet
```bash
# Depuis la racine du projet
bash scripts/test_complete_workflow.sh
```

### Durée Estimée
- ⏱️ **~30-60 secondes** (dépend de la puissance machine)

---

## 📊 Ce Que le Script Teste

### ✅ Workflow LOCATION
| Étape | Action | Vérification |
|-------|--------|--------------|
| 1 | Création Programme | Programme ID créé |
| 2 | Création Unité LOCATION | Unité avec loyer mensuel |
| 3 | Création Client | Email: client.e2e@test.com |
| 4 | Réservation LOCATION | Type: LOCATION, Durée: 12 mois |
| 5 | Paiement Caution | 15% prix (2,250,000 FCFA) |
| 6 | **Validation Caution** | **Signal → Échéance Mois 1 créée** ✅ |
| 7 | Paiement Échéance Mois 1 | 150,000 FCFA |
| 8 | **Validation Échéance 1** | **Signal → Échéance Mois 2 créée** ✅ |

### ✅ Workflow VENTE
| Étape | Action | Vérification |
|-------|--------|--------------|
| 9 | Création Unité VENTE | Prix: 25,000,000 FCFA |
| 10 | Réservation VENTE | Type: VENTE |
| 11 | Paiement Acompte | 20% prix (5,000,000 FCFA) |
| 12 | Validation Acompte | Statut: valide ✅ |

### ✅ Dashboard
- Compteurs cohérents (badge = table)
- Paiements en attente visibles
- Échéances en attente visibles

---

## 🎯 Résultat Attendu

Si tout fonctionne correctement, vous verrez :

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    📊 RÉSUMÉ DU TEST COMPLET                              ║
╚════════════════════════════════════════════════════════════════════════════╝

✅ WORKFLOW LOCATION (12 mois):
   1. Programme créé: ID=123
   2. Unité LOCATION créée: ID=456 (LOC-E2E-01)
   3. Client créé: ID=789 (client.e2e@test.com)
   4. Réservation LOCATION: ID=101
   5. Paiement Caution: ID=202 (2,250,000 FCFA)
   6. Caution Validée → Échéance Mois 1 générée: ID=303
   7. Paiement Échéance Mois 1: ID=404 (150,000 FCFA)
   8. Échéance Mois 1 Validée → Échéance Mois 2 générée: ID=505

✅ WORKFLOW VENTE:
   9. Unité VENTE créée: ID=606 (VENTE-E2E-02)
   10. Réservation VENTE: ID=707
   11. Paiement Acompte: ID=808 (5,000,000 FCFA)
   12. Acompte Validé

✅ VÉRIFICATIONS:
   • Signals fonctionnent correctement ✓
   • Échéances auto-générées ✓
   • Dashboard compteurs cohérents ✓
   • Workflow LOCATION complet ✓
   • Workflow VENTE complet ✓

Status: ✅ TOUS LES TESTS PASSENT
```

---

## 🔍 Vérification Manuelle (Optionnelle)

### 1. Dashboard Commercial
```
URL: http://localhost:8000/ventes/
Login: commercial.e2e@test.com
Password: password123

Vérifier:
✓ Onglet "Validations en Attente"
✓ Badge compteur correct
✓ Items affichés dans le tableau
```

### 2. Django Admin - Échéances
```
URL: http://localhost:8000/admin/sales/echeanceloyer/
Login: admin@scindongo.sn / admin

Vérifier:
✓ Échéance Mois 1 (paiement lié, statut=valide)
✓ Échéance Mois 2 (pas encore payée)
```

### 3. Django Admin - Paiements
```
URL: http://localhost:8000/admin/sales/paiement/

Vérifier:
✓ Caution (type=CAUTION, statut=valide)
✓ Échéance 1 (type=ECHEANCE, statut=valide)
✓ Acompte (type=ACOMPTE, statut=valide)
```

---

## 🐛 Dépannage

### Problème: Container pas en cours d'exécution
```bash
# Démarrer le container
docker-compose up -d

# Attendre 10 secondes
sleep 10

# Relancer le test
bash scripts/test_complete_workflow.sh
```

### Problème: Échéance Mois 1 NON créée
```
Cause possible: Signal non déclenché

Solution:
1. Vérifier core/signals.py (ligne 91)
2. Vérifier que le signal est bien connecté
3. Vérifier logs Django:
   docker-compose logs web | grep -i signal
```

### Problème: Échéance Mois 2 NON créée
```
Cause possible: Signal non déclenché

Solution:
1. Vérifier core/signals.py (ligne 142)
2. Vérifier que paiement.type_paiement == 'ECHEANCE'
3. Vérifier logs Django
```

### Problème: "Programme créé: ID=" vide
```
Cause: Erreur création en base

Solution:
1. Vérifier migrations:
   docker-compose exec web python manage.py showmigrations
2. Appliquer migrations si nécessaire:
   docker-compose exec web python manage.py migrate
3. Relancer le test
```

---

## 📝 Nettoyage Après Test

Le script crée des données de test avec préfixe "E2E". Pour nettoyer :

```bash
# Méthode 1: Via Django shell
docker-compose exec web python manage.py shell << EOF
from catalog.models import Programme
from django.contrib.auth import get_user_model

User = get_user_model()

# Supprimer programme test (cascade supprime tout)
Programme.objects.filter(nom="Test Programme E2E").delete()

# Supprimer utilisateurs test
User.objects.filter(email__contains="e2e@test.com").delete()

print("✓ Données test supprimées")
EOF

# Méthode 2: Via script de nettoyage
docker-compose exec web python manage.py shell << EOF
from sales.models import Reservation, Paiement, EcheanceLoyer
from catalog.models import Programme, Unite
from django.contrib.auth import get_user_model

User = get_user_model()

# Supprimer tout ce qui a "E2E" dans les références
Unite.objects.filter(reference_lot__contains="E2E").delete()
Programme.objects.filter(nom__contains="E2E").delete()
User.objects.filter(email__contains="e2e").delete()

print("✓ Nettoyage complet")
EOF
```

---

## 🎓 Comprendre le Script

### Structure du Script
```bash
# 1. Fonctions utilitaires
print_header()      # Affichage headers
print_success()     # Messages succès
run_django_shell()  # Exécution Python dans Django

# 2. Vérifications préalables
check_container_running()  # Container actif?

# 3. Tests séquentiels
# Chaque test crée un objet et vérifie son ID

# 4. Résumé final
# Affiche tous les IDs créés + statuts
```

### Logique Clé: Génération Échéances
```python
# Signal 1 (core/signals.py ligne 91):
# Trigger: Paiement caution validé
# Action: Créer EcheanceLoyer(numero_mois=1)

# Signal 2 (core/signals.py ligne 142):
# Trigger: Paiement échéance validé
# Action: Créer EcheanceLoyer(numero_mois=N+1)
```

---

## 📊 Métriques de Test

| Métrique | Valeur |
|----------|--------|
| Durée totale | ~30-60 secondes |
| Objets créés | ~15 (Programme, Unités, Users, Reservations, Paiements, Échéances) |
| Signals testés | 2 (Caution → Mois 1, Mois 1 → Mois 2) |
| Workflows testés | 2 (LOCATION + VENTE) |
| Étapes totales | 12 |

---

## ✅ Checklist Post-Test

Après exécution du script, vérifier :

- [ ] Message final "✅ TOUS LES TESTS PASSENT"
- [ ] Aucun message d'erreur rouge (✗)
- [ ] Tous les IDs affichés (non vides)
- [ ] Échéance Mois 1 créée (Signal 1 OK)
- [ ] Échéance Mois 2 créée (Signal 2 OK)
- [ ] Dashboard compteurs cohérents
- [ ] Logs Django sans erreur

Si tous les points sont ✅ → **Système fonctionne correctement** ! 🎉

---

## 🔗 Ressources

- **Script source:** `scripts/test_complete_workflow.sh`
- **Signals:** `core/signals.py` (lignes 91 et 142)
- **Models:** `sales/models.py` (Reservation, Paiement, EcheanceLoyer)
- **Documentation:** `README.md`, `RELEASE_NOTES.md`

---

**Version:** 1.0  
**Date:** December 10, 2025  
**Status:** ✅ Production Ready
