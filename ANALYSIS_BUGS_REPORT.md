╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║               🔍 ANALYSE COMPLÈTE DU PROJET SCINDONGO IMMO                    ║
║                                                                                ║
║                      RAPPORT BUGS & CORRECTIONS - V1.0                        ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝


═══════════════════════════════════════════════════════════════════════════════════
🚨 BUGS CRITIQUES IDENTIFIÉS
═══════════════════════════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG #1 : PAIEMENTS AFFICHENT "✓ VALIDÉ" MAIS RESTENT EN "ATTENTE"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYMPTÔMES :
  • Dans le dashboard commercial "Validations en Attente"
  • Les paiements affichent "✓ Validé" mais restent dans la liste
  • Échéances affichent "⏳ En Attente" mais devraient disparaître si payées

CAUSE RACINE :
  1. Modèle Paiement : champ "statut" (valeurs: enregistre, valide, rejete)
  2. Modèle EcheanceLoyer : champ "statut_paiement" (valeurs: enregistre, valide, rejete)
  3. Quand on valide un Paiement (vue CommercialPaymentValidateView ligne 2256):
     → On change Paiement.statut de 'enregistre' à 'valide'
     → MAIS on n'update PAS EcheanceLoyer.statut_paiement
     → Donc EcheanceLoyer reste bloqué à 'enregistre'
  
  4. Le template commercial_dashboard.html affiche:
     - Paiements avec statut='enregistre' (via get_queryset ligne 2228)
     - Échéances avec statut_paiement='enregistre' (via get_context_data)
     - Mais affiche le badge basé sur Paiement.statut (qui peut être 'valide')
     → INCOHÉRENCE : Le badge affiche "✓ Validé" mais reste dans la table

FICHIERS CONCERNÉS :
  ✗ sales/views.py:2218-2260 (CommercialPaymentValidationListView)
  ✗ sales/views.py:2256 (CommercialPaymentValidateView.post)
  ✗ sales/models.py:398-453 (EcheanceLoyer.statut_paiement)
  ✗ templates/dashboards/commercial_dashboard.html:440-600


SOLUTION :
  1. Quand on valide un Paiement, AUSSI mettre à jour EcheanceLoyer.statut_paiement
  2. OU : Changer la logique pour afficher SEULEMENT les paiements 'enregistre'
     (masquer ceux 'valide' de la liste "Attente")
  3. OU : Créer une vue unifiée pour gérer Paiement + EcheanceLoyer synchronisés

RECOMMANDATION : Approche #1 + #2 = Synchroniser + Masquer dans le template


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG #2 : LOGIQUE VENTE VS LOCATION MÉLANGÉE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYMPTÔMES :
  • Dans le template client_payment_mode_choice.html:
    - Affiche "Financement Bancaire" MÊME pour les locations
    - Les locations ne devraient afficher QUE les paiements directs + caution
  • Dans la vue ClientPaymentModeChoiceView:
    - Pas de vérification si c'est VENTE ou LOCATION
    - Permet de demander financement pour location (invalide métier)

CAUSE RACINE :
  1. Client reservation_confirm.html affiche option "financement" sans condition
  2. ClientPaymentModeChoiceView (ligne 1260) pas de vérification is_vente()
  3. Modèle Reservation a method is_vente() et is_location() mais pas utilisées

FICHIERS CONCERNÉS :
  ✗ templates/sales/client_payment_mode_choice.html:87-110
  ✗ sales/views.py:1238-1310 (ClientPaymentModeChoiceView.get_context_data)
  ✗ sales/views.py:1260 (ClientPaymentModeChoiceView.post)
  ✗ sales/views.py:1313 (ClientDirectPaymentView)
  ✗ sales/views.py:1409 (ClientFinancingRequestView)


SOLUTION :
  1. Ajouter vérification dans ClientPaymentModeChoiceView.dispatch():
     if not reservation.is_vente():
         redirect(payment_mode='direct')
  2. Mettre à jour template pour masquer financement en location
  3. Mettre à jour CommercialDashboard pour séparer VENTE et LOCATION


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG #3 : REDONDANCES ÉCHÉANCES DANS LE DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYMPTÔMES :
  • "Échéances LOCATION à Valider" affiche 4 mois
  • Même Mois 1 apparaît 3+ fois pour réservations différentes
  • Les filtres ne distinguent pas payé vs en attente

CAUSE RACINE :
  1. CommercialDashboardView.get_context_data() crée deux querysets:
     - echeances_en_attente : paiement != null ET statut='enregistre'
     - echeances_non_payees : paiement = null
  2. Mais les deux sont affichées dans MÊME section du template
  3. Le template ne filtre pas les doublons (même échéance peut apparaître 2x)

FICHIERS CONCERNÉS :
  ✗ sales/views.py:1166-1200 (CommercialDashboardView.get_context_data)
  ✗ templates/dashboards/commercial_dashboard.html:520-580


SOLUTION :
  1. Créer deux sections distinctes:
     - "À PAYER" (paiement=null)
     - "À VALIDER" (paiement!=null, statut='enregistre')
  2. Ne PAS afficher paiements validés (statut='valide')
  3. Ajouter count() distincts pour éviter doublons


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG #4 : MISSING SIGNALS.PY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYMPTÔMES :
  • Écheances ne sont pas créées automatiquement
  • Statuts ne se synchronisent pas
  • Audit logs manuels partout

CAUSE RACINE :
  1. sales/signals.py N'EXISTE PAS
  2. Aucun signal post_save sur Paiement pour mettre à jour EcheanceLoyer
  3. Aucun signal post_save sur Reservation pour créer EcheanceLoyer
  4. La création d'échéances est manuelle (utils.py generer_echeances_loyer)

FICHIERS CONCERNÉS :
  ✗ sales/signals.py (INEXISTANT)
  ✗ sales/apps.py (N'enregistre pas les signaux)
  ✗ sales/views.py (creation echances partout)
  ✗ sales/utils.py:generer_echeances_loyer() (fonction utilitaire)


SOLUTION :
  1. Créer sales/signals.py avec:
     - Signal post_save sur Paiement → mettre à jour EcheanceLoyer
     - Signal post_save sur Reservation (location) → générer échéances
  2. Enregistrer dans sales/apps.py
  3. Nettoyer la création manuelle d'échéances dans les vues


═══════════════════════════════════════════════════════════════════════════════════
🔧 CORRECTIONS À APPLIQUER (DANS L'ORDRE)
═══════════════════════════════════════════════════════════════════════════════════

ÉTAPE 1: Créer signals.py ✓
  Fichier : sales/signals.py (NOUVEAU)
  Impact : Synchronise Paiement ↔ EcheanceLoyer

ÉTAPE 2: Fix CommercialPaymentValidateView ✓
  Fichier : sales/views.py ligne 2256
  Impact : Valide les paiements ET les échéances en même temps

ÉTAPE 3: Ajouter vérifications VENTE/LOCATION ✓
  Fichier : sales/views.py ClientPaymentModeChoiceView
  Impact : Empêche les locations d'accéder au financement

ÉTAPE 4: Nettoyer template dashboard ✓
  Fichier : templates/dashboards/commercial_dashboard.html
  Impact : Sépare paiements validés de ceux en attente

ÉTAPE 5: Update CommercialDashboardView ✓
  Fichier : sales/views.py
  Impact : Filtre correctement les paiements/échéances en attente


═══════════════════════════════════════════════════════════════════════════════════
📋 STRUCTURE RECOMMANDÉE POUR LE REFACTORING
═══════════════════════════════════════════════════════════════════════════════════

SÉPARATION VENTE VS LOCATION :

VENTE :
  ├── Étape 1 : Créer réservation + acompte
  ├── Étape 2 : Valider acompte
  ├── Étape 3 : Choisir mode paiement (DIRECT ou FINANCEMENT)
  ├── Étape 4 : Créer financement (optionnel)
  ├── Étape 5 : Créer contrat
  ├── Étape 6 : Signer contrat
  ├── Étape 7 : Enregistrer solde (DIRECT ou financement)
  └── Étape 8 : Commercial valide solde

LOCATION :
  ├── Étape 1 : Créer réservation + durée bail
  ├── Étape 2 : Enregistrer CAUTION (obligatoire)
  ├── Étape 3 : Commercial valide caution
  ├── Étape 4 : Générer échéances (auto, signal)
  ├── Étape 5 : Enregistrer loyer Mois 1
  ├── Étape 6 : Commercial valide loyer Mois 1
  ├── Étape 7 : Générer échéance Mois 2 (auto, signal)
  ├── Étape 8 : Répéter pour chaque mois
  ├── Étape 9 : Créer contrat (après caution validée)
  └── Étape 10 : Signer contrat


═══════════════════════════════════════════════════════════════════════════════════
🎯 PUNCHLIST FINALE (À FAIRE APRÈS LES FIXES)
═══════════════════════════════════════════════════════════════════════════════════

☐ Tester workflow complet VENTE (avec et sans financement)
☐ Tester workflow complet LOCATION (caution → échéances → paiements)
☐ Vérifier que dashboard affiche correctement les statuts
☐ Vérifier que paiements validés disparaissent de "En Attente"
☐ Vérifier que signals créent/mettent à jour automatiquement
☐ Tester API endpoints avec les deux types d'opération
☐ Vérifier les logs d'audit
☐ Tester les permissions COMMERCIAL/CLIENT/ADMIN
☐ Vérifier les routes URL (pas de 404)
☐ Tester les templates (pas de variables manquantes)


═══════════════════════════════════════════════════════════════════════════════════
