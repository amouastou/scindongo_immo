# 📑 INDEX - SCINDONGO IMMO v1.0 Documentation

**Status:** ✅ Production Ready | **Date:** December 10, 2025

---

## 🎯 Quick Links

Start here based on your role:

### 👨‍💼 **Project Manager / PO**
→ Read: **[PRE_MERGE_NOTES.md](PRE_MERGE_NOTES.md)**
- ✅ What changed
- ✅ When is it ready to deploy
- ✅ Deployment checklist

### 👨‍💻 **Developer (Setup & Testing)**
→ Read: **[README.md](README.md)** → [Quick Start Section]
1. Setup: `docker-compose up --build`
2. Tests: `python manage.py test tests.test_suite`
3. Manual verification: See [Testing](#-testing--verification) section

### 🚀 **DevOps / SRE (Deployment)**
→ Read: **[DEPLOYMENT.md](DEPLOYMENT.md)**
- Pre-deployment checklist
- Staging deployment
- Production deployment
- Rollback procedures
- Monitoring setup

### 📖 **Technical Deep Dive**
→ Read: **[RELEASE_NOTES.md](RELEASE_NOTES.md)**
- Detailed changes explained
- Before/after comparisons
- Technical architecture
- Known limitations

---

## 📚 Documentation Structure

```
📄 README.md
   └─ Main documentation (architecture, features, APIs)

📄 PRE_MERGE_NOTES.md
   └─ Quick summary for immediate deployment

📄 RELEASE_NOTES.md
   └─ Detailed technical changelog

📄 DEPLOYMENT.md
   └─ Complete deployment guide

📄 INDEX.md (this file)
   └─ Navigation guide
```

---

## 🚀 Deployment Timeline

### Ready for Staging ✅
- All code complete
- All tests passing
- Documentation complete

### Ready for Production ✅
- Staging verified 24 hours
- Manual tests completed
- Database backup taken
- Monitoring alerts configured

**Estimated Time to Deploy:** 30 minutes (with pre-deployment checklist)

---

## ✅ Key Tasks Before Production

| Task | Time | Who | Status |
|------|------|-----|--------|
| Code review | 20 min | Dev Lead | ✅ |
| Automated tests | 5 min | CI/CD | ✅ |
| Manual testing | 15 min | QA | ⏳ |
| Staging deployment | 15 min | DevOps | ⏳ |
| Production backup | 5 min | DBA | ⏳ |
| Production deployment | 15 min | DevOps | ⏳ |
| Post-deploy verification | 10 min | QA | ⏳ |
| **Total** | **80 min** | **Team** | **⏳** |

---

## 🎯 Feature Summary

### 1. Unified Dashboard
- **Location:** `/ventes/`
- **Who:** Commercial users
- **What:** Single tab "Validations en Attente" with acomptes + échéances

### 2. Search Functionality
- **Location:** Dashboard search bar or `/ventes/commercial/recherche/`
- **Who:** Commercial users
- **What:** Find unit by reference_lot, view all details

### 3. Progressive Échéances (LOCATION)
- **How:** Auto-generated monthly via Django signals
- **When:** 
  - Mois 1: After caution payment validated
  - Mois N+1: After Mois N payment validated
- **Benefit:** Better cash flow visibility

### 4. Fixed UI Bugs
- Dashboard counter now matches table
- No more 404 on "Valider" button
- Clean, aligned code

---

## 🧪 Testing Checklist

### ✅ Automated (Run Once)
```bash
python manage.py test tests.test_suite
# Expected: 14 tests, all pass
```

### ✅ Manual (Before Production)
- [ ] Client: Reserve LOCATION unit
- [ ] Client: Pay caution (15% of unit price)
- [ ] Commercial: Validate caution payment
- [ ] System: Check Month 1 échéance auto-created
- [ ] Client: Pay Month 1 échéance
- [ ] Commercial: Validate échéance payment
- [ ] System: Check Month 2 échéance auto-created
- [ ] Dashboard: Search by reference_lot works
- [ ] Dashboard: Counter badge matches table count

### ✅ API (Optional)
```bash
curl -X POST http://localhost:8000/api/token/ \
  -d '{"email":"admin@scindongo.sn","password":"admin"}'
# Expected: JWT token
```

---

## 📁 File Structure

### Essential Files
```
manage.py                      # Django entry point
entrypoint.sh                  # Docker startup script
docker-compose.yml             # Docker config
.env                           # Environment variables
```

### Application Modules
```
accounts/                      # Users, roles, permissions
catalog/                       # Programs, units, property types
sales/                         # Reservations, payments, contracts
core/                          # Base models, audit, signals
api/                           # REST API
templates/                     # HTML templates
static/                        # CSS, JS, assets
media/                         # User uploads
tests/                         # Automated tests
scripts/                       # Utility scripts
```

### Documentation
```
README.md                      # ← Start here (4 sections)
PRE_MERGE_NOTES.md            # ← Quick deployment check
RELEASE_NOTES.md              # ← Technical details
DEPLOYMENT.md                 # ← Full deployment guide
INDEX.md                       # ← This file
```

---

## 🔗 Important URLs

### Local Development
```
Homepage:        http://localhost:8000/
Admin:           http://localhost:8000/admin/
API:             http://localhost:8000/api/
Dashboard:       http://localhost:8000/ventes/
Search:          http://localhost:8000/ventes/commercial/recherche/
```

### Production (Example)
```
Homepage:        https://scindongo.sn/
Admin:           https://scindongo.sn/admin/
API:             https://scindongo.sn/api/
Dashboard:       https://scindongo.sn/ventes/
Search:          https://scindongo.sn/ventes/commercial/recherche/
```

---

## 🔑 Key Concepts

### Operation Types
- **LOCATION:** Rental workflow (monthly échéances)
- **VENTE:** Sale workflow (one-time payment options)

### Payment Status Flow
```
enregistre (Initial) → valide (Approved) → [rejection: rejete]
```

### Unit Status Flow
```
disponible → reserve → vendu → livre
```

### Échéance Auto-Generation Signals
```
Caution validated → Month 1 created
Month N validated → Month N+1 created
```

---

## 🆘 Troubleshooting

### Problem: Tests failing
- Check: `docker-compose logs web`
- Fix: `docker-compose down -v && docker-compose up --build`

### Problem: Dashboard shows 0 items
- Check: Are you logged in as COMMERCIAL?
- Check: Do items have `statut_paiement='enregistre'`?

### Problem: Échéance not auto-generating
- Check: Signal triggered? See django logs
- Fix: Verify caution payment `statut_paiement='valide'`

### Problem: Can't validate payment
- Check: Button only shows if status is 'enregistre'
- Reason: Design prevents validating already-validated items

---

## 👥 Roles & Permissions

### CLIENT
- View programs & units
- Make reservations
- View own payments
- Make payments
- View contracts

### COMMERCIAL
- View all reservations
- View all payments
- Validate payments → Triggers échéance generation
- Search units by reference
- View dashboard

### ADMIN
- Everything
- Plus: Manage users, roles, configurations

---

## 📊 Database Models (Key)

```
User (accounts.User)
├─ email (unique, login field)
├─ first_name, last_name
├─ roles (M2M: CLIENT, COMMERCIAL, ADMIN)

Programme (catalog.Programme)
├─ nom, description, localization
├─ unites (1:N)

Unite (catalog.Unite)
├─ reference_lot (unique)
├─ prix_ttc
├─ statut (disponible, reserve, vendu, livre)
├─ programme (FK)

Reservation (sales.Reservation)
├─ client (FK to User)
├─ unite (FK)
├─ operation_type (LOCATION, VENTE)
├─ statut (en_cours, confirmee, annulee, expiree)
├─ paiements (1:N)
├─ echances_loyer (1:N) if LOCATION

Paiement (sales.Paiement)
├─ reservation (FK)
├─ montant
├─ type_paiement (CAUTION, ACOMPTE, ECHEANCE, SOLDE)
├─ statut_paiement (enregistre, valide, rejete)

EcheanceLoyer (sales.EcheanceLoyer)
├─ reservation (FK)
├─ numero_mois (1-12+)
├─ montant (loyer mensuel)
├─ paiement (FK, null if unpaid)
├─ statut_paiement (enregistre, valide, rejete)
```

---

## 🎓 Learning Resources

### For New Developers
1. Read README.md [Architecture Overview]
2. Run local tests
3. Explore Django admin at http://localhost:8000/admin/
4. Review models in `sales/models.py`
5. Check signals in `core/signals.py`

### For Deployment Engineers
1. Read DEPLOYMENT.md in full
2. Review entrypoint.sh
3. Understand docker-compose.yml
4. Practice deployment on staging
5. Document your setup

### For QA/Testing
1. Create test accounts (provided in README.md)
2. Follow manual testing checklist above
3. Document any issues found
4. Verify counters match between views

---

## 📞 Support Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Project Lead | [Name] | [email] | [phone] |
| Tech Lead | [Name] | [email] | [phone] |
| DevOps | [Name] | [email] | [phone] |
| On-Call | [Name] | [email] | [phone] |

---

## 🎯 Next Steps

### For Immediate Deployment
1. ✅ Read PRE_MERGE_NOTES.md
2. ✅ Run: `bash scripts/pre_merge_checks.sh`
3. ✅ Expected: "✅ TOUS LES TESTS PASSENT"
4. → Create GitHub PR
5. → Deploy to staging
6. → Manual testing (15 min)
7. → Deploy to production

### Estimated Total Time
- Setup + Testing: 30 min
- Deployment: 30 min
- Verification: 15 min
- **Total: 75 minutes** ✅

---

**Version:** 1.0 | **Date:** December 10, 2025 | **Status:** ✅ Ready for Production

**Questions?** See README.md or DEPLOYMENT.md for detailed answers.
