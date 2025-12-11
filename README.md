# 🏢 SCINDONGO IMMO - Real Estate Management Platform

**Version:** 1.0 | **Status:** ✅ Production Ready | **Date:** December 10, 2025

---

## 📋 Project Overview

SCINDONGO Immo est une plateforme de gestion immobilière Django avec :
- ✅ Gestion des programmes et lots immobiliers
- ✅ Workflow de location avec échéances mensuelles progressives
- ✅ Workflow de vente avec financement bancaire
- ✅ Dashboard commercial unifié
- ✅ Système d'audit complet
- ✅ API REST avec authentification JWT

---

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Requis: Docker + Docker Compose
docker --version
docker-compose --version
```

### 2. Environment Setup
```bash
# Variables autorisées dans .env :
POSTGRES_DB=scindongo_immo
POSTGRES_USER=scindongo
POSTGRES_PASSWORD=scindongo
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
```

### 3. Lancer l'Application
```bash
# Build et démarrage (auto: migrations, superuser, collectstatic)
docker-compose up --build

# Accès:
# - Frontend: http://localhost:8000/
# - Django Admin: http://localhost:8000/admin/
# - API: http://localhost:8000/api/
```

### 4. Default Credentials
```
Email: admin@scindongo.sn
Password: admin
(Créé automatiquement dans entrypoint.sh)
```

---

## 📁 Architecture

```
scindongo_immo/
├── accounts/          # User models, roles, permissions
├── catalog/           # Programmes, Units, Property Types
├── sales/             # Reservations, Payments, Financing, Contracts
├── core/              # Base models, Audit logging, Utils
├── api/               # REST API (DRF + JWT)
├── templates/         # HTML templates
├── static/            # CSS, JS, Assets
├── media/             # User uploads (images, documents)
├── tests/             # Automated test suite
└── scripts/           # Utility scripts
```

---

## 🔑 Key Features

### 1. **User Roles**
- **CLIENT**: Browse, Reserve, Make Payments
- **COMMERCIAL**: Manage Sales, Validate Payments, Search Properties
- **ADMIN**: Full System Control

### 2. **Workflows**

#### 🏘️ LOCATION (Rental)
1. Client books unit → Pays caution (deposit)
2. Commercial validates payment
3. System auto-generates Month 1 échéance
4. Client pays échéance
5. Commercial validates
6. System auto-generates Month 2, etc.

**Key:** Échéances générées progressivement (pas tous les 12 mois d'un coup)

#### 🏠 VENTE (Sale)
1. Client reserves unit → Pays acompte (down payment)
2. Commercial validates
3. Unit status: disponible → réservée → vendue
4. Client can apply for bank financing
5. Optional: Multiple installments via Paiements

### 3. **Dashboard Commercial**
- **Onglet Unique:** "⏳ Validations en Attente"
  - Section 1: Acomptes VENTE (attente validation)
  - Section 2: Échéances LOCATION (attente validation)
- **Barre Recherche:** Chercher lot par référence
- **Compteurs:** Badge montre nombre items à valider

---

## 🔧 Database

### Models Core
- `Programme` → Multiple `Unite` (lots)
- `Reservation` → Multiple `Paiement` + `Contrat` + `Financement`
- `EcheanceLoyer` → Auto-generated per month (LOCATION only)
- `JournalAudit` → All user actions logged

### Key Fields
- **Reservation.operation_type**: "LOCATION" ou "VENTE"
- **Paiement.statut_paiement**: "enregistre", "valide", "rejete"
- **EcheanceLoyer.statut_paiement**: Same as above
- **Unite.statut**: "disponible", "reserve", "vendu", "livre"

---

## 📊 Signals & Automation

### Auto-Generated Échéances
1. **Signal 1** (core/signals.py:91):
   - Trigger: Paiement caution validée
   - Action: Generate Mois 1 échéance

2. **Signal 2** (core/signals.py:142):
   - Trigger: Any échéance payment validated
   - Action: Generate next month échéance

**Important:** Signals trigger in `sales.views.CommercialPaymentValidateView`

---

## 🧪 Testing

### Run Tests
```bash
# Inside container
docker-compose exec web python manage.py test tests.test_suite

# Results: 14 test methods covering models, views, signals, permissions
```

### Manual Testing
1. Create client account
2. Browse programs & units
3. Make LOCATION reservation + caution payment
4. Login as commercial
5. Validate caution
6. Verify Month 1 échéance created
7. Pay & validate
8. Verify Month 2 créated

---

## 🛠️ Management Commands

```bash
# Run from inside container
docker-compose exec web python manage.py <command>

# Key commands:
makemigrations          # Create migration files
migrate                 # Apply migrations
shell                   # Django shell
createsuperuser         # Create admin user
collectstatic           # Gather static files
generer_echeances_automatiques  # Monthly échéance generation (27th)
```

---

## 🐛 Troubleshooting

### 1. Server Not Starting
```bash
# Check logs
docker-compose logs web

# Usually: Syntax error or migration issue
# Fix: docker-compose down -v && docker-compose up --build
```

### 2. 404 on Payment Validation
- **Cause:** Paiement.statut_paiement ≠ "enregistre"
- **Fix:** Dashboard only shows items with correct status

### 3. Échéances Not Generating
- **Cause:** Signals not triggered or caution not validated
- **Fix:** Check CommercialPaymentValidateView called signal.send()

### 4. Database Orphaned Data
```bash
# Clean orphaned échéances
bash scripts/cleanup_db.sh
```

---

## 📝 API Endpoints

### Authentication
```
POST   /api/token/                 # Get JWT token
POST   /api/token/refresh/         # Refresh token
```

### Core Resources
```
GET    /api/programmes/            # List programs
GET    /api/programmes/{id}/       # Get program details
GET    /api/unites/                # List units
GET    /api/reservations/          # List reservations
POST   /api/reservations/          # Create reservation
GET    /api/paiements/             # List payments
POST   /api/paiements/             # Create payment
GET    /api/paiements/{id}/valider/ # Validate payment
```

### Filters
```
/api/reservations/?operation_type=LOCATION
/api/reservations/?statut=en_cours
/api/paiements/?statut_paiement=enregistre
/api/echeances/?is_en_retard=true
```

---

## 🔒 Permissions

### Role-Based Access Control
- `IsAdminScindongo`: Require admin role
- `IsCommercial`: Require commercial role
- `IsClient`: Require client role
- `IsClientOwnerOrAdminOrCommercial`: Object-level (client sees own data)

### Example:
```python
# Client can only see their own reservations
GET /api/reservations/  → Returns only client's reservations
```

---

## 📋 Important Configuration

### settings.py Key Settings
```python
AUTH_USER_MODEL = 'accounts.User'         # Email-based login
LANGUAGE_CODE = 'fr-fr'                   # French UI
TIME_ZONE = 'Africa/Dakar'                # Senegal timezone
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',
]
CORS_ALLOWED_ORIGINS = ['localhost:3000', 'localhost:5173']
```

---

## 🚀 Deployment

### Production Checklist
- [ ] Change `DJANGO_SECRET_KEY` in .env
- [ ] Set `DJANGO_DEBUG=0`
- [ ] Configure database to production PostgreSQL
- [ ] Set up HTTPS/SSL
- [ ] Configure email backend
- [ ] Enable logging to file/monitoring
- [ ] Run migrations
- [ ] Collect static files
- [ ] Test all workflows

### Docker Production
```bash
# Build image
docker build -t scindongo-immo:latest .

# Run container
docker run -d \
  -e DJANGO_DEBUG=0 \
  -e DJANGO_SECRET_KEY=your-secret \
  -p 8000:8000 \
  --name scindongo-immo \
  scindongo-immo:latest
```

---

## 📚 Documentation Files

- **PRE_MERGE_NOTES.md** - Changes summary & pre-merge checklist
- **entrypoint.sh** - Docker startup script
- **schema.sql** - Database schema export
- **requirements.txt** - Python dependencies

---

## 🤝 Development

### Adding New Model
1. Create in app `models.py` → Inherit from `TimeStampedModel`
2. Register in `admin.py`
3. Create serializer in `api/serializers.py`
4. Create viewset in `api/views.py`
5. Add to `api/urls.py` router
6. Run migrations: `makemigrations` → `migrate`

### Git Workflow
```bash
git checkout -b feature/your-feature
# Make changes
git add .
git commit -m "Your message"
git push origin feature/your-feature
# Create PR on GitHub
```

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs -f web`
2. Review documentation in this README
3. Check model definitions in respective app `models.py`
4. Review API examples in `api/views.py`

---

## 📄 License

Proprietary - SCINDONGO Immo

---

**Last Updated:** December 10, 2025 | **Python:** 3.11 | **Django:** 5.0 | **PostgreSQL:** 15
