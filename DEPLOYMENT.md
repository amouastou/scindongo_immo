# 🚀 DEPLOYMENT GUIDE - SCINDONGO IMMO v1.0

**Last Updated:** December 10, 2025 | **Status:** ✅ Production Ready

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Development Environment](#development-environment)
3. [Testing & Verification](#testing--verification)
4. [Staging Deployment](#staging-deployment)
5. [Production Deployment](#production-deployment)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Rollback Procedure](#rollback-procedure)

---

## ✅ Pre-Deployment Checklist

### Code Quality
- [ ] All tests pass: `python manage.py test tests.test_suite`
- [ ] Django check passes: `python manage.py check`
- [ ] No syntax errors: `python -m py_compile sales/views.py core/signals.py`
- [ ] Code review completed
- [ ] No hardcoded secrets in code
- [ ] No debug print statements

### Database
- [ ] Database backed up: `pg_dump -U scindongo scindongo_immo > backup_$(date +%Y%m%d_%H%M%S).sql`
- [ ] Migrations reviewed: `python manage.py showmigrations`
- [ ] Database schema documented
- [ ] No pending migrations

### Configuration
- [ ] `.env` configured for target environment
- [ ] `DJANGO_DEBUG=0` in production
- [ ] `DJANGO_SECRET_KEY` changed from default
- [ ] `ALLOWED_HOSTS` includes production domain
- [ ] Email backend configured
- [ ] CORS settings appropriate for frontend URL
- [ ] Logging configured to file/external service
- [ ] Static files location configured

### Documentation
- [ ] API documentation reviewed
- [ ] Known issues documented
- [ ] Deployment procedure verified
- [ ] Rollback procedure tested
- [ ] Emergency contacts listed

---

## 🏗️ Development Environment

### Initial Setup
```bash
# Clone repository
git clone https://github.com/amouastou/scindongo_immo.git
cd scindongo_immo

# Create .env file
cat > .env << EOF
POSTGRES_DB=scindongo_immo
POSTGRES_USER=scindongo
POSTGRES_PASSWORD=scindongo
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=dev-secret-change-in-production
DJANGO_DEBUG=1
EOF

# Start development server
docker-compose up --build

# Verify
curl http://localhost:8000/
# Expected: 200 OK with SCINDONGO Immo homepage
```

### Stop Development Server
```bash
docker-compose down
```

### Clean Database (for testing)
```bash
docker-compose down -v  # Remove volumes too
docker-compose up --build  # Fresh database with demo data
```

---

## 🧪 Testing & Verification

### Automated Tests
```bash
# Run entire test suite
docker-compose exec web python manage.py test tests.test_suite

# Expected output:
# test_is_location (tests.test_suite.ReservationModelTest) ... ok
# test_is_vente (tests.test_suite.ReservationModelTest) ... ok
# [... 12 more tests ...]
# Ran 14 tests in X.XXs
# OK
```

### Django System Checks
```bash
docker-compose exec web python manage.py check

# Expected:
# System check identified no issues (0 silenced).
```

### Pre-Merge Verification Script
```bash
bash scripts/pre_merge_checks.sh

# Expected output:
# ✅ TOUS LES TESTS PASSENT - PRÊT POUR LA FUSION
# Exit code: 0
```

### Manual Test Flow (5 minutes)

**1. Client Creates Reservation (LOCATION)**
```
Login: client.test@example.com / password
Navigate: Accueil → Programmes → Select Unit
Click: Réserver
Fill: Form (all fields required)
Submit: Confirmation page shows
Status: Réservation en cours
```

**2. Client Makes Caution Payment**
```
Navigate: Tableau de Bord → Paiements
Click: Payer Caution
Fill: Amount = Unit Price × 15%
Submit: Payment recorded (status: enregistre)
```

**3. Commercial Validates Payment**
```
Login: mame.fatou.ndao@scindongo.sn / password (COMMERCIAL role)
Navigate: Dashboard → Onglet "Validations en Attente"
Verify: Caution payment appears in Section 1
Click: Valider button
Expected: Status changes to "Validé" ✓
```

**4. System Auto-Generates Month 1 Échéance**
```
Verify: EcheanceLoyer created in database
- numero_mois=1
- montant = Loyer mensuel
- statut_paiement = 'enregistre' initially? NO (unpaid)
- paiement = NULL
```

**5. Client Pays First Échéance**
```
Navigate: Dashboard → Tableau Paiements
Click: Payer for Month 1 échéance
Submit: Payment recorded (status: enregistre)
```

**6. Commercial Validates Échéance Payment**
```
Navigate: Dashboard → Onglet "Validations en Attente"
Click: Valider for Month 1
Expected: Status changes to "Validé" ✓
```

**7. System Auto-Generates Month 2 Échéance**
```
Verify: EcheanceLoyer created
- numero_mois=2
- paiement = NULL (unpaid)
```

**Success Criteria:** All steps complete without errors, echéances auto-generate correctly ✓

---

## 🌐 Staging Deployment

### Environment Setup
```bash
# Create staging .env
cat > .env.staging << EOF
POSTGRES_DB=scindongo_immo_staging
POSTGRES_USER=scindongo_staging
POSTGRES_PASSWORD=staging-password-here
POSTGRES_HOST=db-staging
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=staging-secret-change-before-prod
DJANGO_DEBUG=0
ALLOWED_HOSTS=staging.scindongo.sn,localhost:8000
CORS_ALLOWED_ORIGINS=https://staging-frontend.scindongo.sn
EOF

# Load into environment
export $(cat .env.staging | xargs)
```

### Build & Deploy to Staging
```bash
# Build Docker image
docker build -t scindongo-immo:staging-$(date +%Y%m%d) .

# Tag latest
docker tag scindongo-immo:staging-$(date +%Y%m%d) scindongo-immo:staging-latest

# Push to registry (if using Docker Hub/Private Registry)
docker push scindongo-immo:staging-latest

# Run staging container
docker run -d \
  --name scindongo-staging \
  -p 8001:8000 \
  --env-file .env.staging \
  scindongo-immo:staging-latest
```

### Staging Verification
```bash
# Check container health
docker ps | grep scindongo-staging

# Check logs
docker logs scindongo-staging | head -50

# Run migrations
docker exec scindongo-staging python manage.py migrate

# Test API
curl -X POST http://staging.scindongo.sn:8001/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@scindongo.sn","password":"admin"}'

# Expected: JWT token in response
```

### Staging Testing
- Run full test suite (see [Testing & Verification](#testing--verification))
- Test with real data samples
- Load test (simulate 100 concurrent users)
- Test email notifications
- Verify backups work

---

## 🏭 Production Deployment

### Pre-Production Database Backup
```bash
# Backup from production server
ssh prod-server
docker-compose exec db pg_dump -U scindongo scindongo_immo > \
  backup_prod_$(date +%Y%m%d_%H%M%S).sql

# Download to local machine
scp prod-server:backup_prod_*.sql ./backups/

# Verify backup integrity
pg_restore --list backup_prod_*.sql | head -20
```

### Production Environment Setup
```bash
# Copy .env.staging to .env.production
cp .env.staging .env.production

# Update critical settings
cat >> .env.production << EOF
DJANGO_DEBUG=0
POSTGRES_HOST=prod-db-host
POSTGRES_PASSWORD=$(generate_random_password)
DJANGO_SECRET_KEY=$(generate_random_secret)
ALLOWED_HOSTS=scindongo.sn,www.scindongo.sn
CORS_ALLOWED_ORIGINS=https://scindongo.sn
SECURE_SSL_REDIRECT=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
EOF

# ⚠️ CRITICAL: Never commit .env.production to git!
# Store in secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)
```

### Build & Deploy to Production
```bash
# Build production image
docker build -t scindongo-immo:prod-$(date +%Y%m%d) .

# Tag latest
docker tag scindongo-immo:prod-$(date +%Y%m%d) scindongo-immo:prod-latest

# Deploy with docker-compose
docker-compose -f docker-compose.yml up -d --build

# Or: Deploy to Kubernetes (if applicable)
kubectl set image deployment/scindongo-web \
  web=scindongo-immo:prod-latest
```

### Post-Deployment Steps
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create/update superuser if needed
docker-compose exec web python manage.py createsuperuser

# Verify no orphaned data
docker-compose exec web bash scripts/cleanup_db.sh

# Check system status
docker-compose exec web python manage.py check
```

---

## ✔️ Post-Deployment Verification

### Health Checks
```bash
# Check containers running
docker-compose ps
# All containers should show "Up" or "healthy"

# Check logs for errors
docker-compose logs web | grep -i error | head -10

# Test homepage
curl -s http://localhost:8000/ | grep -q "SCINDONGO" && echo "✓ Homepage OK"

# Test API endpoint
curl -s http://localhost:8000/api/ | grep -q "Token" && echo "✓ API OK"

# Test database connection
docker-compose exec web python manage.py dbshell << 'EOF'
SELECT COUNT(*) FROM accounts_user;
EOF
```

### Functional Verification
1. **Admin Panel:**
   - Navigate to http://localhost:8000/admin/
   - Login with admin credentials
   - Verify all models visible

2. **Client Dashboard:**
   - Login as client
   - View programs & units
   - Verify can place reservation

3. **Commercial Dashboard:**
   - Login as commercial
   - View "Validations en Attente" tab
   - Verify search functionality

4. **API:**
   - Get token: `POST /api/token/`
   - List resources: `GET /api/programmes/`
   - Verify JWT auth working

### Database Verification
```bash
# Check critical tables
docker-compose exec web python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from catalog.models import Programme
from sales.models import Reservation

User = get_user_model()
print(f"Users: {User.objects.count()}")
print(f"Programmes: {Programme.objects.count()}")
print(f"Reservations: {Reservation.objects.count()}")
EOF
```

### Performance Verification
```bash
# Check response times
time curl -s http://localhost:8000/api/programmes/ > /dev/null

# Check database query count (with DEBUG=True temporarily)
# Expected: < 20 queries per request
```

---

## 📊 Monitoring & Alerts

### Application Monitoring
```bash
# Log aggregation (example with ELK stack)
docker-compose exec web tail -f /var/log/django.log

# Key metrics to monitor:
# - Response time (p95: < 500ms)
# - Error rate (< 0.1%)
# - Database connection pool (< 20 connections)
# - Disk space (> 20% free)
# - Memory usage (< 80%)
```

### Set Up Alerts
1. **HTTP Errors:** Alert if 500 errors > 10 per minute
2. **Response Time:** Alert if p95 > 1000ms
3. **Database:** Alert if connections > 25
4. **Disk Space:** Alert if free space < 10%
5. **Memory:** Alert if usage > 85%

### Logging Configuration
```python
# In settings.py for production:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django_error.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'ERROR',
    },
}
```

---

## 🔄 Rollback Procedure

### If Critical Issues After Deployment

**Step 1: Identify Issue**
```bash
# Check logs for errors
docker-compose logs web | tail -100

# Common issues:
# - Migration failed
# - Configuration error (ALLOWED_HOSTS, CORS, etc.)
# - Database connection issue
# - Static files not found
```

**Step 2: Quick Fix Options**

**Option A: Code/Config Issue (No Database Changes)**
```bash
# Stop current container
docker-compose down

# Fix code/config
git revert HEAD
# OR: Fix .env file

# Restart
docker-compose up --build

# Test
curl http://localhost:8000/
```

**Option B: Database Migration Issue**
```bash
# Restore from backup
docker-compose down -v

# Restore database
docker exec scindongo_db_1 psql -U scindongo < backup_prod_YYYYMMDD_HHMMSS.sql

# Revert code to previous version
git revert HEAD

# Restart
docker-compose up --build

# Verify
curl http://localhost:8000/
```

**Option C: Full Rollback**
```bash
# Stop all containers
docker-compose down -v

# Switch to previous Docker image
docker run -d \
  --name scindongo-immo \
  -p 8000:8000 \
  --env-file .env \
  scindongo-immo:prod-PREVIOUS_DATE

# Restore database
docker exec scindongo_db_1 psql -U scindongo < backup_prod_PREVIOUS_DATE.sql

# Verify all services
docker-compose up
```

### Communication
1. **Notify Team:** Alert team about rollback
2. **Update Status Page:** If public-facing
3. **Post-Mortem:** Document root cause
4. **Prevent Future:** Add pre-deployment test to catch issue

---

## 🔍 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **503 Service Unavailable** | App not started | Check logs: `docker-compose logs web` |
| **Database Connection Error** | DB not ready | Wait 10s for DB, then retry |
| **Static Files 404** | Not collected | Run `collectstatic` after deploy |
| **CORS Error** | Domain not in CORS_ALLOWED_ORIGINS | Add frontend URL to .env |
| **JWT Token Invalid** | SECRET_KEY changed | Use same SECRET_KEY as before |
| **Emails Not Sending** | Email backend not configured | Configure SMTP settings in .env |

---

## 📞 Escalation Path

1. **L1 Support:** Check logs, restart container
2. **L2 DevOps:** Check infrastructure, scaling, monitoring
3. **L3 Engineering:** Code review, database restoration
4. **On-Call:** If issue critical and urgent

**On-Call Contact:** [Add contact info]

---

## 📝 Deployment Checklist Template

```markdown
## Deployment: [Version] - [Date]

**Pre-Deployment:**
- [ ] All tests pass
- [ ] Code review approved
- [ ] Database backed up
- [ ] Staging verified

**Deployment:**
- [ ] Built Docker image
- [ ] Updated .env file
- [ ] Ran migrations
- [ ] Collected static files
- [ ] Verified health checks

**Post-Deployment:**
- [ ] Admin panel accessible
- [ ] Client dashboard working
- [ ] Commercial dashboard working
- [ ] No errors in logs
- [ ] Database queries < 20 per page

**Sign-Off:**
- Deployed by: [Name]
- Verified by: [Name]
- Timestamp: [Date/Time UTC]
```

---

## 📚 Additional Resources

- Django Deployment: https://docs.djangoproject.com/en/5.0/howto/deployment/
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
- PostgreSQL Backup: https://www.postgresql.org/docs/15/backup.html
- Production Checklist: https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

---

**Last Updated:** December 10, 2025  
**Version:** 1.0  
**Status:** ✅ Production Ready
