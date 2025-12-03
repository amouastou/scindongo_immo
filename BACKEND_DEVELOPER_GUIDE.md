# SCINDONGO Immo Backend – Guide Développeur

## Démarrage Rapide

### 1. Lancer le projet
```bash
docker-compose up --build
```

Accès :
- **Site** : http://localhost:8000/
- **Admin Django** : http://localhost:8000/admin/
- **API** : http://localhost:8000/api/

Credentials par défaut :
- **Email** : `amadoubousso50@gmail.com`
- **Password** : `Admin123!`

### 2. Migrations de base de données
```bash
# Générer les migrations après modification des modèles
docker-compose exec web python manage.py makemigrations

# Appliquer les migrations
docker-compose exec web python manage.py migrate
```

### 3. Charger les fixtures (optionnel)
```bash
# Les fixtures sont en demo seulement (pour éviter les erreurs d'intégrité)
docker-compose exec web python manage.py loaddata accounts/fixtures/demo_roles.json
docker-compose exec web python manage.py loaddata accounts/fixtures/demo_users.json
docker-compose exec web python manage.py loaddata catalog/fixtures/demo_programmes.json
docker-compose exec web python manage.py loaddata sales/fixtures/demo_sales.json
```

### 4. Accéder au shell Django
```bash
docker-compose exec web python manage.py shell
```

### 5. Voir les logs en temps réel
```bash
docker-compose logs -f web
```

### 6. Réinitialiser la base de données
```bash
docker-compose down -v
docker-compose up --build
```

## Patterns et Bonnes Pratiques

### Ajouter un nouveau modèle

1. **Créer le modèle** dans l'app appropriée (ex: `sales/models.py`)
   ```python
   from core.models import TimeStampedModel
   from core.choices import SomeStatus  # Utiliser TextChoices
   
   class MyModel(TimeStampedModel):
       name = models.CharField(max_length=255)
       statut = models.CharField(
           max_length=20,
           choices=SomeStatus.choices,
           default=SomeStatus.INITIAL
       )
   ```

2. **Créer le serializer** dans `api/serializers.py`
   ```python
   class MyModelSerializer(serializers.ModelSerializer):
       class Meta:
           model = MyModel
           fields = "__all__"
       
       def validate(self, attrs):
           # Validations métier ici
           return attrs
   ```

3. **Créer le ViewSet** dans `api/views.py`
   ```python
   class MyModelViewSet(viewsets.ModelViewSet):
       queryset = MyModel.objects.all()
       serializer_class = MyModelSerializer
       permission_classes = [IsAuthenticated, IsAdminOrCommercial]
       filter_backends = [DjangoFilterBackend, filters.SearchFilter]
       filterset_fields = ["statut"]
       search_fields = ["name"]
       
       def get_queryset(self):
           qs = super().get_queryset()
           # Filtrer par rôle si nécessaire
           return qs
   ```

4. **Enregistrer dans le routeur** dans `api/urls.py`
   ```python
   router.register(r'mymodels', MyModelViewSet)
   ```

5. **Générer + appliquer les migrations**
   ```bash
   docker-compose exec web python manage.py makemigrations
   docker-compose exec web python manage.py migrate
   ```

### Ajouter une nouvelle permission

Dans `accounts/permissions.py` :

```python
class IsMyRoleOrOwner(BasePermission):
    """Description."""
    
    def has_permission(self, request, view):
        # Niveau de permission (toute requête)
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Niveau d'objet (accès spécifique)
        return obj.owner == request.user
```

### Tester l'API avec curl

```bash
# Login (obtenir token JWT)
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"amadoubousso50@gmail.com","password":"Admin123!"}'

# Utiliser le token
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/programmes/

# Filtrer
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/unites/?programme=<uuid>&statut_disponibilite=disponible"

# Créer
curl -X POST http://localhost:8000/api/reservations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client": "<uuid>",
    "unite": "<uuid>",
    "acompte": 5000000,
    "statut": "en_cours"
  }'
```

### Utiliser Python pour tester

```python
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

# Créer un utilisateur test
user = User.objects.create_user(
    email="test@example.com",
    password="testpass123"
)

# Se connecter
client = APIClient()
client.force_authenticate(user=user)

# Tester un endpoint
response = client.get('/api/programmes/')
print(response.status_code)
print(response.data)
```

## Points d'Extension Clés

### Ajouter un endpoint personnalisé

```python
class MyViewSet(viewsets.ModelViewSet):
    # ...existing config...
    
    @action(detail=True, methods=["post"])
    def custom_action(self, request, pk=None):
        obj = self.get_object()
        # Logique métier
        return Response({"message": "ok"})

# Accès : POST /api/mymodels/<id>/custom_action/
```

### Ajouter un signal automatique

Dans `core/signals.py` :

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=MyModel)
def my_model_saved(sender, instance, created, **kwargs):
    if created:
        # Faire quelque chose après création
        audit_log(None, instance, "my_model_created", {"name": instance.name})
```

Enregistrer dans `core/apps.py` (déjà fait).

## Debugging

### Voir les requêtes SQL
```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as context:
    # Code à profiler
    pass

for query in context.captured_queries:
    print(query['sql'])
```

### Logs d'audit
```python
from core.models import JournalAudit

# Voir les 10 dernières actions
logs = JournalAudit.objects.all().order_by('-created_at')[:10]
for log in logs:
    print(f"{log.action} on {log.objet_type} by {log.acteur}")
```

## Conventions de Code

- **Noms de champs** : French (nom, prenom, telephone, email)
- **Noms de modèles** : English + PascalCase (Reservation, not Réservation)
- **Statuts** : TextChoices dans `core/choices.py`, French labels
- **Serializers** : `{Model}Serializer`
- **ViewSets** : `{Model}ViewSet`
- **Permissions** : Nom descriptif (IsAdminScindongo, IsClientOwner, etc.)
- **Signaux** : Dans `core/signals.py`
- **Tests** : Dans `tests.py` (root) ou `app/tests.py` (si complexe)

## Ressources Internes

- `.github/copilot-instructions.md` : Instructions pour AI agents
- `BACKEND_V1_SUMMARY.md` : Résumé des améliorations V1
- `requirements.txt` : Dépendances Python
- `docker-compose.yml` : Configuration Docker
- `scindongo_immo/settings.py` : Configuration Django

## FAQ

**Q: Comment ajouter un rôle utilisateur ?**
A: Via l'admin Django : http://localhost:8000/admin/accounts/role/

**Q: Comment changer le mot de passe du superuser ?**
A: 
```bash
docker-compose exec web python manage.py changepassword amadoubousso50@gmail.com
```

**Q: Comment exporter les données ?**
A:
```bash
docker-compose exec web python manage.py dumpdata > backup.json
```

**Q: Comment charger des données ?**
A:
```bash
docker-compose exec web python manage.py loaddata backup.json
```

**Q: Comment voir les migrations créées ?**
A:
```bash
ls -la sales/migrations/
```

## Support

Pour toute question, consulter :
- `.github/copilot-instructions.md` pour l'architecture
- `catalog/models.py`, `sales/models.py` pour les modèles
- `accounts/permissions.py` pour les permissions
- `api/views.py` pour les endpoints
