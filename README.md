SCINDONGO Immo – Version unifiée

Cette archive correspond à la version **finale unifiée** de la plateforme immobilière SCINDONGO Immo.

## 1. Prérequis

- Docker
- Docker Compose

## 2. Variables d'environnement

Un fichier `.env` (ou équivalent) peut être utilisé pour définir les variables suivantes :

```env
POSTGRES_DB=scindongo_immo
POSTGRES_USER=scindongo
POSTGRES_PASSWORD=scindongo
POSTGRES_HOST=db
POSTGRES_PORT=5432

DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
```

## 3. Lancement du projet

Depuis la racine du projet :

```bash
docker compose up --build
```

Le conteneur web démarre Gunicorn sur le port `8000`.

- Front / site : http://localhost:8000/
- Administration Django : http://localhost:8000/admin/

## 4. Superuser par défaut

Au démarrage, le script `entrypoint.sh` vérifie qu'un superuser existe et en crée un si besoin.

Identifiants par défaut :

- **email** : `amadoubousso50@gmail.com`
- **mot de passe** : `Admin123!`

Ces valeurs peuvent être surchargées dans `settings.py` via :

```python
DEFAULT_SUPERUSER_EMAIL = "..."
DEFAULT_SUPERUSER_PASSWORD = "..."
```

## 5. Fixtures

Les fixtures JSON (`accounts/fixtures`, `catalog/fixtures`, `sales/fixtures`) sont fournies **à titre d'exemples** mais **ne sont plus chargées automatiquement** au démarrage pour éviter les erreurs d'intégrité.

Si vous souhaitez les utiliser, vous pourrez :

```bash
docker compose exec web python manage.py loaddata accounts/fixtures/demo_roles.json
docker compose exec web python manage.py loaddata accounts/fixtures/demo_users.json
docker compose exec web python manage.py loaddata catalog/fixtures/demo_programmes.json
docker compose exec web python manage.py loaddata catalog/fixtures/demo_chantier.json
docker compose exec web python manage.py loaddata sales/fixtures/demo_sales.json
```

**Attention :** selon l'évolution des modèles, il est possible que ces fixtures nécessitent des ajustements manuels (cohérence des clés étrangères, champs NOT NULL, etc.).

Pour une démo propre, il est recommandé de créer progressivement vos objets via l'admin Django.

## 6. Résumé des choix techniques

- Base : projet retravaillé `SCINDONGO_IMMO_FINAL_FIXTURES` (structure plus moderne).
- Point d'entrée : script `entrypoint.sh` simplifié et fiabilisé.
- Plus de chargement automatique de fixtures au démarrage (démarrage robuste, sans crash).
- Superuser créé automatiquement si nécessaire.
- `collectstatic` exécuté systématiquement pour garantir le CSS/JS du /admin.

=======
# scindongo_immo
Projet master2
>>>>>>> ebbcc2420cf3f6f5d995e030d1f21a77db2b0ec1
