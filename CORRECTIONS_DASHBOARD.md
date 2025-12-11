# 🔧 Corrections Dashboard Commercial - Incohérence Paiements/Validations

## 🔴 Problème Identifié

**Section "Validations en Attente"** affichait :
- Des paiements **LOCATION** (cautions + échéances) dans la section "Paiements **VENTE** à Valider"
- Des paiements avec statut **"✓ Validé"** dans une section "**En Attente**"
- Incohérence entre le statut du paiement et le statut de l'échéance associée

## ✅ Corrections Appliquées

### FIX 1 : Filtrer les paiements VENTE uniquement
**Fichier**: `sales/views.py` ligne 689-694  
**Avant**: `payments_qs = Paiement.objects.filter(statut="enregistre")`  
**Après**: 
```python
payments_qs = Paiement.objects.filter(
    statut=PaiementStatus.ENREGISTRE,
    type_paiement__in=[PaiementType.ACOMPTE, PaiementType.SOLDE]  # VENTE uniquement
)
```
**Impact**: Ne récupère que les paiements de type ACOMPTE/SOLDE (VENTE). Les cautions et échéances (LOCATION) sont exclues.

---

### FIX 2 : Synchroniser cautions lors validation
**Fichier**: `sales/views.py` ligne 2283-2305 (CommercialPaymentValidateView)  
**Avant**: Ignorait les cautions lors de la validation  
**Après**: 
```python
elif paiement.type_paiement == PaiementType.CAUTION:
    # Cautions: pas d'EcheanceLoyer, juste marquer comme validée
    # Quand caution est validée, générer les échéances mensuelles
    reservation = paiement.reservation
    if reservation.is_location():
        try:
            from .utils import generer_echeances_loyer
            from datetime import date
            # Générer échéances depuis la date du bail
            generer_echeances_loyer(reservation, date.today())
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur création échéances: {e}")
```
**Impact**: Quand un paiement de caution est validé, les échéances mensuelles sont automatiquement générées.

---

### FIX 3 : Utiliser le bon queryset dans le contexte
**Fichier**: `sales/views.py` ligne 713  
**Avant**: `ctx["paiements"] = paiements_qs.filter(statut=PaiementStatus.ENREGISTRE)[:20]`  
**Après**: `ctx["paiements"] = ctx["pending_payments"][:20]`  
**Impact**: Le contexte affiche maintenant les paiements filtrés VENTE + statut enregistré, pas TOUS les paiements.

---

## 📊 Résultat Attendu

Après les corrections, le dashboard commercial affichera :

### Section "Paiements VENTE à Valider" 
- ✅ SEULEMENT les paiements avec `type_paiement IN ['acompte', 'solde']`
- ✅ SEULEMENT ceux avec `statut='enregistre'`
- ❌ Pas de cautions (ce sont des LOCATION)
- ❌ Pas d'échéances de loyer (ce sont des LOCATION)

### Section "Échéances LOCATION à Valider"
- ✅ Échéances avec paiement enregistré (`statut_paiement='enregistre'`)
- ✅ Cautions avec paiement enregistré
- ❌ Aucun paiement avec statut='valide'

---

## 🧪 Vérification

Après déploiement, vérifier que :
1. ✓ La section "Paiements VENTE" est vide (aucune caution ni échéance)
2. ✓ La section "Échéances LOCATION" ne contient que les paiements enregistrés
3. ✓ Quand on valide une caution, elle génère les échéances

---

**Date**: 11 Décembre 2025  
**Fichiers modifiés**: `sales/views.py`  
**Tests requis**: Oui - Dashboard commercial + Validations paiements/échéances
