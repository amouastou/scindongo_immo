# 🔒 Planning Sécurité - SCINDONGO Immo

**Date :** 18 décembre 2024  
**Status :** Audit de sécurité complet

---

## ✅ CE QUI EST DÉJÀ FAIT

### 1. Sécurité des Emails ✅
- ✅ **Unicité des emails** : Vérification dans le modèle User (unique=True)
- ✅ **Validation du format** : Regex + Django validators
- ✅ **Validation du domaine** : Vérification DNS MX
- ✅ **Existence de l'email** : Vérification SMTP RCPT TO
- ✅ **Domaines autorisés** : Liste noire des domaines non vérifiables (mail.com, hotmail, etc.)
- ✅ **Vérification par token** : Token unique 32 bytes, expiration 24h
- ✅ **Compte inactif** : is_active=False jusqu'à vérification email

### 2. Authentication & Autorisation ✅
- ✅ **Mot de passe fort** : Django password validators (longueur, complexité, common passwords)
- ✅ **Hashing sécurisé** : PBKDF2 avec SHA256 (Django par défaut)
- ✅ **Rôles utilisateurs** : CLIENT, COMMERCIAL, ADMIN avec permissions
- ✅ **Permissions object-level** : IsClientOwnerOrAdminOrCommercial
- ✅ **Protection CSRF** : CsrfViewMiddleware actif
- ✅ **Session sécurisée** : SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SECURE (à activer en prod)

### 3. Audit & Traçabilité ✅
- ✅ **Audit middleware** : Logs de toutes les actions sensibles
- ✅ **JournalAudit model** : Stockage des logs avec IP, user-agent, payload
- ✅ **Audit sur inscriptions** : Logs des tentatives (succès, échec)
- ✅ **Audit sur réservations** : Logs des créations, modifications
- ✅ **Audit sur paiements** : Logs des transactions

### 4. Performance & Stabilité ✅
- ✅ **Connexions PostgreSQL** : CONN_MAX_AGE=600 (réutilisation)
- ✅ **Cache Redis** : Actif pour les pages publiques
- ✅ **Compression GZIP** : Réduction 60-80% de la bande passante
- ✅ **Optimisation Gunicorn** : 4 workers × 2 threads = 8 req simultanées
- ✅ **Timeout SMTP** : 5s (évite les blocages)

---

## 🔴 CE QUI RESTE À FAIRE - PRIORITÉ HAUTE

### 1. Rate Limiting (Anti-Spam/Brute Force) 🔴 CRITIQUE
**Problème :** Actuellement, pas de limite sur les tentatives d'inscription, connexion, etc.

**Risques :**
- ❌ Attaque par force brute sur les mots de passe
- ❌ Spam d'inscriptions avec des faux emails
- ❌ Déni de service (DoS) par surcharge du serveur

**Solution à implémenter :**
```
Utiliser django-ratelimit ou django-axes

Limites recommandées :
- Inscription : 3 tentatives / 10 minutes par IP
- Connexion : 5 tentatives / 10 minutes par IP + email
- Envoi email : 2 tentatives / 5 minutes
- API : 100 requêtes / minute par utilisateur
```

**Fichiers à modifier :**
- `accounts/views.py` : RegisterView, LoginView
- `accounts/email_service.py` : send_verification_email
- `api/views.py` : Tous les ViewSets
- `requirements.txt` : Ajouter django-ratelimit

**Estimation :** 2-3 heures

---

### 2. CAPTCHA (Anti-Bot) 🔴 CRITIQUE
**Problème :** Pas de protection contre les bots automatisés

**Risques :**
- ❌ Inscriptions massives automatisées
- ❌ Spam sur les formulaires de contact
- ❌ Scraping automatique des données

**Solution à implémenter :**
```
Google reCAPTCHA v3 (invisible, basé sur le score)

Avantages :
- Gratuit jusqu'à 1 million de vérifications/mois
- Invisible pour les utilisateurs légitimes
- Score de 0 à 1 (0=bot, 1=humain)
```

**Formulaires à protéger :**
- ✅ Inscription (RegisterForm)
- ✅ Connexion (LoginForm)
- ✅ Réinitialisation mot de passe
- ✅ Contact / Demande d'information

**Fichiers à modifier :**
- `requirements.txt` : Ajouter django-recaptcha
- `scindongo_immo/settings.py` : Configuration RECAPTCHA keys
- `accounts/forms.py` : Ajouter ReCaptchaField
- `templates/accounts/register.html` : Ajouter script reCAPTCHA

**Estimation :** 1-2 heures

---

### 3. Protection Mot de Passe 🟠 IMPORTANT
**Problème :** Pas de contraintes supplémentaires sur les mots de passe faibles

**Amélioration à faire :**
```
Ajouter des validateurs personnalisés :

- Pas de mots de passe dans la blacklist (password, 123456, etc.)
- Pas de répétition du nom/prénom/email
- Au moins 1 majuscule
- Au moins 1 chiffre
- Au moins 1 caractère spécial
- Minimum 10 caractères (au lieu de 8)
```

**Fichiers à modifier :**
- `accounts/validators.py` : Nouveau fichier avec validateurs custom
- `scindongo_immo/settings.py` : AUTH_PASSWORD_VALIDATORS
- `accounts/forms.py` : Afficher les règles dans le formulaire

**Estimation :** 1 heure

---

### 4. Réinitialisation Mot de Passe Sécurisée 🟠 IMPORTANT
**Problème :** Système de réinitialisation basique sans protection

**À implémenter :**
```
- Token unique avec expiration courte (1 heure)
- Un seul usage du token
- Rate limiting sur les demandes
- Notification par email si réinitialisation effectuée
- Invalidation de toutes les sessions actives après reset
```

**Fichiers à créer/modifier :**
- `accounts/views.py` : PasswordResetView, PasswordResetConfirmView
- `accounts/models.py` : PasswordResetToken model
- `templates/accounts/password_reset.html`
- `accounts/urls.py` : Ajouter les routes

**Estimation :** 2-3 heures

---

### 5. Session & Cookie Sécurisés 🟠 IMPORTANT
**Problème :** Configuration par défaut, pas optimale pour la production

**À configurer :**
```python
# settings.py (pour la PRODUCTION uniquement)

SESSION_COOKIE_SECURE = True  # HTTPS uniquement
SESSION_COOKIE_HTTPONLY = True  # Déjà fait
SESSION_COOKIE_SAMESITE = 'Lax'  # Protection CSRF
SESSION_COOKIE_AGE = 3600  # 1 heure (au lieu de 2 semaines)

CSRF_COOKIE_SECURE = True  # HTTPS uniquement
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Déconnexion automatique après inactivité
SESSION_SAVE_EVERY_REQUEST = True
```

**Fichiers à modifier :**
- `scindongo_immo/settings.py`

**Estimation :** 30 minutes

---

### 6. Protection Injection SQL 🟢 BON (mais à vérifier)
**Status :** Django protège automatiquement avec l'ORM

**À vérifier :**
```
Parcourir TOUT le code et s'assurer qu'il n'y a AUCUNE requête SQL brute :

❌ JAMAIS faire : 
   User.objects.raw(f"SELECT * FROM users WHERE email='{email}'")
   
✅ TOUJOURS faire :
   User.objects.filter(email=email)
```

**Fichiers à auditer :**
- `accounts/views.py`
- `sales/views.py`
- `catalog/views.py`
- `api/views.py`

**Estimation :** 1 heure (audit complet)

---

### 7. Protection XSS (Cross-Site Scripting) 🟢 BON (mais à renforcer)
**Status :** Django échappe automatiquement le HTML dans les templates

**À vérifier/améliorer :**
```
1. Vérifier qu'on utilise {{ variable }} et PAS {{ variable|safe }}
2. Sanitiser les entrées riches (WYSIWYG editor)
3. Ajouter Content-Security-Policy headers
```

**Fichiers à auditer :**
- Tous les templates `templates/**/*.html`
- Rechercher `|safe` et `mark_safe()`
- Vérifier les champs avec HTML (descriptions, commentaires)

**À ajouter :**
```python
# settings.py
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

**Estimation :** 1-2 heures

---

### 8. Upload de Fichiers Sécurisé 🟠 IMPORTANT
**Problème :** Actuellement, uploads possibles (photos programmes, chantier, etc.)

**Risques :**
- ❌ Upload de scripts malveillants (.php, .exe, .sh)
- ❌ Upload de fichiers trop volumineux (DoS)
- ❌ Exécution de code via upload

**À implémenter :**
```
1. Whitelist des extensions autorisées :
   - Images : .jpg, .jpeg, .png, .webp (PAS .svg, .gif animé)
   - PDF : .pdf uniquement
   
2. Vérification du type MIME réel (pas juste l'extension)

3. Limite de taille : 5 MB par fichier

4. Stockage hors du dossier web (ou protection .htaccess)

5. Renommage aléatoire des fichiers

6. Scan antivirus (optionnel mais recommandé en prod)
```

**Fichiers à modifier :**
- `catalog/models.py` : Ajouter validators sur ImageField
- `sales/models.py` : Ajouter validators sur FileField
- `core/validators.py` : Nouveau fichier avec validateurs custom
- `scindongo_immo/settings.py` : FILE_UPLOAD_MAX_MEMORY_SIZE

**Estimation :** 2-3 heures

---

### 9. Journalisation & Monitoring 🟡 MOYEN
**Status :** Audit logs en place, mais pas de monitoring en temps réel

**À améliorer :**
```
1. Logs centralisés :
   - Erreurs serveur (500)
   - Tentatives de connexion échouées
   - Modifications sensibles (paiements, contrats)

2. Alertes automatiques :
   - Email admin si > 5 tentatives de connexion échouées
   - Email admin si erreur critique (500)
   - Email admin si pic de trafic anormal

3. Dashboard de monitoring :
   - Nombre d'utilisateurs actifs
   - Nombre de tentatives échouées
   - Temps de réponse moyen
```

**Outils recommandés :**
- Sentry (gratuit jusqu'à 5000 erreurs/mois)
- Grafana + Prometheus (open source)
- Django-axes pour logs de connexion

**Estimation :** 3-4 heures

---

### 10. HTTPS & SSL/TLS 🔴 CRITIQUE (Production uniquement)
**Problème :** En développement = HTTP. En production = DOIT être HTTPS

**À configurer pour la production :**
```
1. Certificat SSL (Let's Encrypt gratuit)

2. Redirection automatique HTTP → HTTPS

3. HSTS (HTTP Strict Transport Security)

4. Configuration Nginx/Apache :
   - SSL protocols: TLSv1.2, TLSv1.3
   - Ciphers forts uniquement
   - OCSP Stapling
```

**Fichiers à modifier :**
- `scindongo_immo/settings.py` :
  ```python
  SECURE_SSL_REDIRECT = True  # Redirection HTTPS
  SECURE_HSTS_SECONDS = 31536000  # 1 an
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  ```

- Configuration serveur web (Nginx/Apache)

**Estimation :** 2-3 heures (avec config serveur)

---

### 11. Backup & Récupération 🟡 MOYEN
**Problème :** Pas de système de backup automatique

**À implémenter :**
```
1. Backup PostgreSQL automatique :
   - Dump quotidien de la base de données
   - Rotation des backups (garder 30 jours)
   - Stockage hors site (AWS S3, Google Cloud)

2. Backup des fichiers uploadés (media/)

3. Backup du code (déjà fait via Git)

4. Plan de restauration documenté
```

**Outils recommandés :**
- pg_dump + cron job
- AWS S3 ou Google Cloud Storage
- django-dbbackup

**Estimation :** 2-3 heures

---

### 12. Protection API (si exposition publique) 🟡 MOYEN
**Status :** API en place avec JWT auth, mais peut être renforcée

**À ajouter :**
```
1. Rate limiting par endpoint :
   - GET : 100 req/min
   - POST : 20 req/min
   - DELETE : 10 req/min

2. Pagination obligatoire (éviter SELECT * FROM)

3. Filtres validés (éviter injections)

4. Throttling par utilisateur

5. API versioning (/api/v1/)

6. Documentation Swagger/OpenAPI
```

**Fichiers à modifier :**
- `api/views.py` : Ajouter throttling
- `scindongo_immo/settings.py` : REST_FRAMEWORK config
- `requirements.txt` : Ajouter drf-spectacular

**Estimation :** 2-3 heures

---

## 📊 PLANNING PRIORISÉ

### 🔴 PRIORITÉ 1 - CRITIQUE (À FAIRE IMMÉDIATEMENT)
**Temps total estimé : 6-9 heures**

1. **Rate Limiting** (2-3h)
2. **CAPTCHA** (1-2h)
3. **Réinitialisation Mot de Passe** (2-3h)
4. **HTTPS/SSL** (1h config, à faire avant la production)

### 🟠 PRIORITÉ 2 - IMPORTANT (AVANT MISE EN PRODUCTION)
**Temps total estimé : 8-12 heures**

5. **Protection Mot de Passe** (1h)
6. **Session Sécurisée** (30min)
7. **Upload Fichiers** (2-3h)
8. **Protection XSS** (1-2h)
9. **Audit Injection SQL** (1h)
10. **Backup** (2-3h)

### 🟡 PRIORITÉ 3 - MOYEN (AMÉLIORATION CONTINUE)
**Temps total estimé : 5-7 heures**

11. **Monitoring** (3-4h)
12. **Protection API** (2-3h)

---

## 📋 CHECKLIST FINALE AVANT PRODUCTION

```
□ Rate limiting activé sur inscription/connexion
□ CAPTCHA activé sur tous les formulaires publics
□ Mots de passe forts obligatoires (10 caractères min)
□ Réinitialisation mot de passe sécurisée
□ Sessions configurées en mode sécurisé
□ HTTPS activé + certificat SSL
□ Upload de fichiers validé et limité
□ Protection XSS vérifiée
□ Aucune requête SQL brute
□ Backup automatique configuré
□ Monitoring actif (Sentry/Grafana)
□ Logs centralisés
□ Rate limiting API
□ Documentation sécurité complète
□ Tests de pénétration effectués (optionnel mais recommandé)
```

---

## 🎯 RECOMMANDATION FINALE

**Pour une mise en production RAPIDE et SÉCURISÉE :**

1. **Cette semaine (Priorité 1)** :
   - Rate Limiting
   - CAPTCHA
   - Réinitialisation mot de passe

2. **Semaine prochaine (Priorité 2)** :
   - Upload sécurisé
   - Session sécurisée
   - Protection XSS
   - Backup

3. **Avant lancement public (Priorité 3)** :
   - HTTPS/SSL
   - Monitoring
   - Tests de charge

---

**Total temps estimé : 19-28 heures de développement**

**Avec votre rythme, c'est faisable en 1-2 semaines ! 🚀**

---

## 📝 NOTES IMPORTANTES

### Ce qui est DÉJÀ très bien fait :
- ✅ Validation email complète (rare de voir ça !)
- ✅ Audit logs complets
- ✅ Permissions granulaires
- ✅ Performance optimisée

### Ce qui DOIT être fait AVANT la production :
- 🔴 Rate Limiting (sinon risque d'attaque)
- 🔴 CAPTCHA (sinon spam garanti)
- 🔴 HTTPS (sinon mots de passe en clair sur le réseau)

### Ce qui peut attendre un peu :
- 🟡 Monitoring avancé
- 🟡 Protection API renforcée

---

**Voulez-vous que je commence par implémenter les éléments PRIORITÉ 1 ? 🚀**
