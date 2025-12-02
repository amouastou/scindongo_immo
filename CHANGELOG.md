# CHANGELOG – SCINDONGO Immo (version unifiée)

## v1.0 – Version unifiée à partir de deux projets

### Base retenue

- **Base principale** : projet récent `SCINDONGO_IMMO_FINAL_FIXTURES`
  - Contient déjà une organisation plus moderne du Docker / entrypoint.
  - Orientation claire vers PostgreSQL + Gunicorn.

- **Projet historique** : `scindongo_immo_full`
  - Project globalement fonctionnel mais avec une orchestration plus simple et moins robuste (chaîne de commandes dans `docker-compose.yml`, pas d'entrypoint dédié).
  - Reste une référence fonctionnelle mais n'est plus la base officielle.

### Décisions clés

1. **Choix de la base officielle**
   - Le projet **`SCINDONGO_IMMO_FINAL_FIXTURES`** est choisi comme base, car il offre une structure Docker plus claire, un découpage plus propre et une meilleure séparation des responsabilités (entrypoint, Gunicorn, etc.).

2. **Correction / simplification de l'entrypoint**
   - Réécriture complète de `entrypoint.sh` pour :
     - Attendre PostgreSQL proprement (test de connexion avec `psycopg2`).
     - Appliquer les migrations (`python manage.py migrate --noinput`).
     - Créer un superuser par défaut s'il n'existe pas (`amadoubousso50@gmail.com` / `Admin123!`).
     - Lancer `collectstatic`.
     - Démarrer Gunicorn sur `0.0.0.0:8000`.

3. **Gestion des fixtures**
   - Les anciens mécanismes de chargement automatique des fixtures au démarrage sont **supprimés** pour éviter les erreurs d'intégrité (NOT NULL, clés étrangères manquantes, etc.).
   - Les fixtures restent présentes dans le dépôt pour un chargement manuel ultérieur, au besoin.

4. **Stabilité du démarrage**
   - L’objectif est d’assurer que :
     - `docker compose up --build` ne plante pas sur des problèmes de fixtures.
     - Les migrations passent.
     - Le superuser est disponible.
     - L’interface d’administration Django se charge avec son CSS standard (fichiers statiques collectés).

### Ce qui est hérité / abandonné

- Hérité du **projet historique** :
  - Schéma fonctionnel d’ensemble (apps `accounts`, `catalog`, `sales`, `core`, etc.).
  - Logique métier principale.

- Optimisé / modernisé via le **projet récent unifié** :
  - Orchestration Docker + Gunicorn + entrypoint dédié.
  - Process d’initialisation de la base de données.
  - Stratégie de gestion des fixtures (manuel plutôt qu’automatique et fragile).

