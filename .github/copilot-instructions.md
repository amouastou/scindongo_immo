# SCINDONGO Immo – AI Coding Agent Instructions

## Project Overview
SCINDONGO Immo is a Django-based real estate management platform with a PostgreSQL backend, REST API, and role-based access control. The application manages property programs, units, reservations, payments, financing, and contracts across three user types: Clients, Commercials, and Admins.

## Architecture Overview

### Core Components
- **accounts**: Custom user model, role-based permissions, authentication views
- **catalog**: Property programs, units, property types, models, construction site tracking
- **sales**: Client management, reservations, payments, financing, contracts
- **api**: REST API viewsets for all models (DRF + JWT authentication)
- **core**: Abstract TimeStampedModel, document management, audit logging

### Key Design Pattern: TimeStampedModel
All domain models inherit from `core.models.TimeStampedModel` which provides:
- UUID primary key (`id`)
- `created_at` and `updated_at` auto-managed timestamps
- Example: `catalog.models.Programme`, `sales.models.Reservation`

### User Authentication & Roles
- Custom `accounts.models.User` uses **email as USERNAME_FIELD** (not username)
- Three role codes: `"CLIENT"`, `"COMMERCIAL"`, `"ADMIN"`
- Users access roles via `user.roles.all()` and helper properties:
  - `user.is_client` → has CLIENT role
  - `user.is_commercial` → has COMMERCIAL role
  - `user.is_admin_scindongo` → has ADMIN role
- Default superuser created in `entrypoint.sh` if not exists

### Role-Based Permissions
Located in `accounts.permissions.py`:
- `IsAdminScindongo`: Checks `is_admin_scindongo` or superuser/staff status
- `IsCommercial`: Checks `is_commercial` or superuser/staff status
- `IsClient`: Checks `is_client` or superuser/staff status
- Used in REST API viewsets to restrict endpoints

### Authorization Mixin for Views
`accounts.mixins.RoleRequiredMixin` gates template views:
```python
class ClientDashboardView(RoleRequiredMixin, TemplateView):
    required_roles = ["CLIENT"]  # List of role codes
```

## Data Model Relationships

### Property Catalog
```
Programme (project)
  ├─ multiple TypeBien (property types: apartment, villa, etc.)
  ├─ multiple ModeleBien (commercial models per type)
  │   └─ surface_hab_m2, prix_base_ttc
  └─ multiple Unite (physical units/lots)
      ├─ statut: disponible, reserve, vendu, livre
      └─ related to ModeleBien

Construction Progress
  ├─ EtapeChantier (construction phases)
  ├─ AvancementChantier (phase progress tracking)
  └─ PhotoChantier (progress photos)
```

### Sales Pipeline
```
Client (user + profile data)
  └─ multiple Reservations
      ├─ Unite (reserved unit)
      ├─ statut: en_cours, confirmee, annulee, expiree
      ├─ multiple Paiements
      ├─ Contrat (1:1) – with PDF, signature logs
      └─ Financement (1:1) – bank financing
          ├─ BanquePartenaire
          ├─ statut: soumis, en_etude, accepte, refuse, clos
          └─ multiple Echeances (schedule)
```

## Key Workflows

### Running the Application
```bash
# Build and start (auto-runs migrations, creates superuser)
docker-compose up --build

# Access via:
# http://localhost:8000/              # Homepage
# http://localhost:8000/admin/        # Django admin
# http://localhost:8000/api/          # API root
```

### Database Migrations
Migrations are **auto-run** in `entrypoint.sh` for apps: `accounts`, `core`, `catalog`, `sales`.
To manually run:
```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Loading Demo Fixtures (Manual)
Fixtures are **NOT auto-loaded** to prevent integrity errors:
```bash
docker-compose exec web python manage.py loaddata accounts/fixtures/demo_users.json
docker-compose exec web python manage.py loaddata catalog/fixtures/demo_programmes.json
docker-compose exec web python manage.py loaddata sales/fixtures/demo_sales.json
```

### Static Files
`collectstatic` is auto-run in `entrypoint.sh` to ensure Django admin CSS/JS load.

## Code Patterns & Conventions

### Naming Conventions
- **Model status fields**: Use French choices, snake_case codes (e.g., `statut="en_cours"`, `statut="confirmee"`)
- **User-facing text**: French labels in Meta verbose_name
- **Field names**: French (nom, prenom, telephone, email)
- **Serializers**: Named `{Model}Serializer` in `api/serializers.py`
- **ViewSets**: Named `{Model}ViewSet` in `api/views.py`

### API Conventions
- REST API uses `djangorestframework-simplejwt` for token auth
- All endpoints require `IsAuthenticated` permission by default
- ViewSets typically allow CRUD + custom `@action` methods
- CORS configured for `localhost:3000` and `localhost:5173` (frontend dev servers)

### Audit Trail
`core.utils.audit_log(user, obj, action, payload, request)` logs user actions:
- Stored in `core.models.JournalAudit`
- Used in views like `sales.views.StartReservationView` to track reservations

### Serializer Nesting
Complex serializers nest related objects:
- `ReservationSerializer` includes `client`, `unite`, `paiements`, `contrat`, `financement`
- Use `read_only=True` for nested details in list views vs. detail views

## Important Configuration Notes

### settings.py Key Settings
- **AUTH_USER_MODEL**: `'accounts.User'` (custom user with email login)
- **LANGUAGE_CODE**: `'fr-fr'` – all UI defaults to French
- **TIME_ZONE**: `'Africa/Dakar'`
- **REST_FRAMEWORK**: JWT auth + SessionAuthentication, all endpoints require auth by default
- **CORS_ALLOWED_ORIGINS**: Frontend dev servers on ports 3000, 5173

### Environment Variables (.env)
```env
POSTGRES_DB=scindongo_immo
POSTGRES_USER=scindongo
POSTGRES_PASSWORD=scindongo
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
```

## Backend V1 Improvements (Latest)

### Status Enumerations (core/choices.py)
All status fields now use Django `TextChoices` for better type safety and maintainability:
- `ProgrammeStatus`: brouillon, actif, archive
- `UniteStatus`: disponible, reserve, vendu, livre
- `ReservationStatus`: en_cours, confirmee, annulee, expiree
- `ContratStatus`: brouillon, signe, annule
- `PaiementStatus`: enregistre, valide, rejete
- `FinancementStatus`: soumis, en_etude, accepte, refuse, clos
- `MoyenPaiement`: virement, cheque, espece, carte

### Enhanced Permissions (accounts/permissions.py)
- `IsClientOwnerOrAdminOrCommercial`: Object-level permission for client data
- `IsReservationOwnerOrAdminOrCommercial`: Object-level permission for reservations
- These allow clients to only see their own data while admins/commercials see all

### Improved ViewSets with Filtering
All main ViewSets now include:
- **get_queryset()**: Filters by user role automatically
  - Clients see only THEIR reservations, payments, contracts, financing
  - Admin/Commercial see all
- **DjangoFilterBackend**: Filter by status, client, programme, etc.
- **SearchFilter**: Full-text search on relevant fields (nom, email, etc.)
- **OrderingFilter**: Sort results
- Examples:
  - `/api/reservations/?statut=en_cours` – filter by status
  - `/api/reservations/?client=<id>` – filter by client
  - `/api/paiements/?moyen=virement` – filter by payment method
  - `/api/programmes/?search=bayakh` – search by name

### Business Logic Validation
- `ReservationSerializer`: Validates acompte ≤ price, prevents double-booking
- `ContratSerializer`: Validates that reservation is `confirmee` before contract creation
- `FinancementSerializer`: Validates financing amount ≤ unit price
- `PaiementSerializer`: Ensures total payments don't exceed unit price
- Auto-update: Reservations set Unite status (disponible → reserve → vendu)

### Audit Logging
- `core/signals.py`: Auto-log on Reservation, Contrat, Paiement, Financement create/update
- `core/utils.audit_log()`: Manual logging in views for user-initiated actions
- `JournalAudit` model: Stores actor, action, object, payload, IP, user-agent

### Testing
- `tests.py`: Basic test suite covering:
  - Permission tests (client can't see other's data)
  - Validation tests (acompte > price fails, etc.)
  - Authentication tests

## Important Configuration Notes

### settings.py Key Settings
- **AUTH_USER_MODEL**: `'accounts.User'` (custom user with email login)
- **LANGUAGE_CODE**: `'fr-fr'` – all UI defaults to French
- **TIME_ZONE**: `'Africa/Dakar'`
- **REST_FRAMEWORK**: JWT auth + SessionAuthentication, all endpoints require auth by default
- **CORS_ALLOWED_ORIGINS**: Frontend dev servers on ports 3000, 5173

### Environment Variables (.env)
```env
POSTGRES_DB=scindongo_immo
POSTGRES_USER=scindongo
POSTGRES_PASSWORD=scindongo
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
```

## Common Development Tasks

### Adding a New Model
1. Create in appropriate app (e.g., `sales/models.py`)
2. Inherit from `core.models.TimeStampedModel` for auto UUID + timestamps
3. Register in `{app}/admin.py` for Django admin
4. Create serializer in `api/serializers.py`
5. Create viewset in `api/views.py` (use `rest_framework.viewsets.ModelViewSet`)
6. Add to `api/urls.py` router
7. Run migrations: `makemigrations` → `migrate`

### Adding API Endpoint with Role Restrictions
```python
from accounts.permissions import IsAdminScindongo
from rest_framework import viewsets

class ProgrammeViewSet(viewsets.ModelViewSet):
    queryset = Programme.objects.all()
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAuthenticated, IsAdminScindongo]
```

### Template Context Patterns
- Dashboards use `RoleRequiredMixin` for role gating
- Context methods override `get_context_data()` to add model querysets
- Example: `ClientDashboardView` adds `reservations`, `paiements` to context

## Testing & Debugging

### Accessing Django Shell
```bash
docker-compose exec web python manage.py shell
```

### Viewing Logs
```bash
docker-compose logs -f web
docker-compose logs -f db
```

### Resetting Database
```bash
docker-compose down -v
docker-compose up --build
```

## File Structure Reference
- `scindongo_immo/settings.py` – Django configuration
- `scindongo_immo/urls.py` – Main URL routing
- `api/urls.py` – REST API router registration
- `api/views.py` – REST API viewsets
- `api/serializers.py` – DRF serializers for all models
- `accounts/permissions.py` – Role-based permission classes
- `accounts/mixins.py` – View mixins like RoleRequiredMixin
- `entrypoint.sh` – Docker startup script (migrations, superuser, collectstatic)

## Cautions & Anti-Patterns

1. **Don't bypass role checks**: Always use permission classes or RoleRequiredMixin
2. **Don't modify status values manually**: Use defined choices in models
3. **Fixtures may need updates**: When model fields change, fixtures must be adjusted (foreign keys, NOT NULL constraints)
4. **Email is the unique identifier**: Never rely on username for user lookup
5. **Always include audit logs**: For user-initiated state changes, call `audit_log()` in views
6. **Respect French localization**: Choices, verbose names, and UI text should be French

---

*Last updated: December 2, 2025 | Python 3.11 | Django 5.0 | PostgreSQL 15 | DRF | django-filter*
