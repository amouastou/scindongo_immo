# 🔒 GUIDE COMPLET : CONFIGURATION HTTPS/SSL - SCINDONGO IMMO

**Date :** 18 décembre 2024  
**Status :** ✅ IMPLÉMENTÉ ET TESTÉ

---

## 📋 CE QUI A ÉTÉ FAIT

### ✅ Configuration Conditionnelle HTTPS/SSL

**Système intelligent à 2 modes :**
1. **Mode DÉVELOPPEMENT** (localhost) : HTTPS désactivé
2. **Mode PRODUCTION** (serveur réel) : HTTPS activé automatiquement

**Avantages :**
- ✅ Fonctionne en local sans certificat SSL
- ✅ S'active automatiquement en production
- ✅ Aucune modification de code nécessaire au déploiement
- ✅ Contrôle via variable d'environnement `PRODUCTION_MODE`

---

## 🎯 COMMENT ÇA MARCHE

### Variable d'environnement

Dans `.env` :
```env
# Mode développement (localhost)
PRODUCTION_MODE=0  ← HTTP, cookies non sécurisés

# Mode production (serveur réel)
PRODUCTION_MODE=1  ← HTTPS, cookies sécurisés, HSTS activé
```

### Configuration automatique

#### MODE DÉVELOPPEMENT (`PRODUCTION_MODE=0`)
```
✅ HTTPS/SSL DÉSACTIVÉ
  - Pas de redirection HTTPS
  - Cookies fonctionnent en HTTP
  - HSTS désactivé  
  - Session expire après 2 semaines
  - X-Frame-Options: SAMEORIGIN
  - Compatible localhost
```

#### MODE PRODUCTION (`PRODUCTION_MODE=1`)
```
✅ HTTPS/SSL ACTIVÉ
  - Redirection automatique HTTP → HTTPS
  - Cookies HTTPS uniquement (SESSION_COOKIE_SECURE=True)
  - HSTS activé (31536000 secondes = 1 an)
  - Session expire après 1 heure d'inactivité
  - X-Frame-Options: DENY
  - Protection renforcée
```

---

## 🧪 TESTS EFFECTUÉS

### Test 1 : Mode Développement ✅
```bash
# Dans .env : PRODUCTION_MODE=0
docker compose down && docker compose up -d
docker compose exec web python /app/check_https_config.py
```

**Résultat :**
```
🔓 MODE DÉVELOPPEMENT : HTTPS/SSL désactivé (localhost)
  - SECURE_SSL_REDIRECT:   False
  - SECURE_HSTS_SECONDS:   0
  - SESSION_COOKIE_SECURE: False
  - SESSION_COOKIE_AGE:    1209600 (336 heures)
```

### Test 2 : Mode Production ✅
```bash
# Dans .env : PRODUCTION_MODE=1
docker compose down && docker compose up -d
docker compose exec web python /app/check_https_config.py
```

**Résultat :**
```
🔒 MODE PRODUCTION : HTTPS/SSL activé
  - SECURE_SSL_REDIRECT:   True
  - SECURE_HSTS_SECONDS:   31536000
  - SESSION_COOKIE_SECURE: True
  - SESSION_COOKIE_AGE:    3600 (1 heure)
```

---

## 📂 FICHIERS MODIFIÉS

### 1. `scindongo_immo/settings.py`
Ajout de la configuration conditionnelle HTTPS basée sur `PRODUCTION_MODE`.

**Lignes ajoutées : ~75 lignes**

### 2. `.env`
Ajout de la variable `PRODUCTION_MODE=0` pour le développement.

### 3. `.env.example`
Documentation complète des variables d'environnement avec exemples.

### 4. `docker-compose.yml`
Ajout de `PRODUCTION_MODE: "${PRODUCTION_MODE:-0}"` pour passer la variable au conteneur.

### 5. `check_https_config.py`
Script de vérification de la configuration HTTPS actuelle.

---

## 🚀 UTILISATION

### En développement (localhost)

**Configuration :** `.env`
```env
PRODUCTION_MODE=0
DJANGO_DEBUG=1
SITE_URL=http://localhost:8000
```

**Commandes :**
```bash
docker compose up -d
# Site accessible : http://localhost:8000
```

### En production (serveur réel)

#### Étape 1 : Obtenir un certificat SSL

**Option A : Let's Encrypt (GRATUIT et recommandé)**
```bash
# Installer Certbot
sudo apt install certbot python3-certbot-nginx

# Obtenir le certificat
sudo certbot --nginx -d votre-domaine.com -d www.votre-domaine.com

# Renouvellement automatique
sudo certbot renew --dry-run
```

**Option B : SSL payant (Namecheap, DigiCert, etc.)**

#### Étape 2 : Configurer Nginx/Apache

**Nginx** (`/etc/nginx/sites-available/scindongo`):
```nginx
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Étape 3 : Activer le mode production

**Configuration :** `.env`
```env
PRODUCTION_MODE=1
DJANGO_DEBUG=0
SITE_URL=https://votre-domaine.com
DJANGO_SECRET_KEY=GÉNÉRER_UNE_CLÉ_FORTE_UNIQUE
DJANGO_ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

**Commandes :**
```bash
docker compose down
docker compose up -d --build

# Vérifier la configuration
docker compose exec web python /app/check_https_config.py
```

**Vous devriez voir :**
```
🔒 MODE PRODUCTION : HTTPS/SSL activé
```

---

## 🔍 VÉRIFICATION HTTPS EN PRODUCTION

### 1. Test dans le navigateur
```
https://votre-domaine.com
```
- ✅ Cadenas vert visible
- ✅ Certificat valide
- ✅ HTTPS actif

### 2. Test des headers
```bash
curl -I https://votre-domaine.com
```

**Headers attendus :**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

### 3. Test de la redirection HTTP → HTTPS
```bash
curl -I http://votre-domaine.com
```

**Résultat attendu :**
```
HTTP/1.1 301 Moved Permanently
Location: https://votre-domaine.com/
```

### 4. Test SSL Labs
Tester votre certificat : https://www.ssllabs.com/ssltest/

**Score attendu : A ou A+**

---

## ⚠️ PROBLÈMES COURANTS & SOLUTIONS

### Problème 1 : "Site non sécurisé" en local

**Cause :** Mode production activé en local sans certificat.

**Solution :**
```env
# Dans .env
PRODUCTION_MODE=0
```

### Problème 2 : "Too many redirects" en production

**Cause :** Nginx/Apache + Django font tous les 2 des redirections.

**Solution :** Dans Nginx, ajouter :
```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

### Problème 3 : Cookies ne fonctionnent pas après activation HTTPS

**Cause :** HSTS activé, navigateur force HTTPS.

**Solution :** 
1. Vider le cache du navigateur
2. En Chrome : chrome://net-internals/#hsts → Delete domain

### Problème 4 : Certificat SSL expiré

**Cause :** Renouvellement automatique Let's Encrypt échoué.

**Solution :**
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## 📊 CHECKLIST DÉPLOIEMENT PRODUCTION

```
□ Certificat SSL obtenu (Let's Encrypt ou payant)
□ Nginx/Apache configuré avec SSL
□ .env configuré avec PRODUCTION_MODE=1
□ DJANGO_DEBUG=0
□ DJANGO_SECRET_KEY changée (clé forte unique)
□ DJANGO_ALLOWED_HOSTS configuré
□ SITE_URL=https://votre-domaine.com
□ docker compose up --build exécuté
□ Vérification : check_https_config.py montre "MODE PRODUCTION"
□ Test navigateur : Cadenas vert visible
□ Test curl : Redirection HTTP → HTTPS fonctionne
□ Test headers : HSTS, X-Frame-Options, etc. présents
□ Test SSL Labs : Score A/A+
□ Renouvellement auto Let's Encrypt configuré (cronjob)
□ Backup du certificat SSL effectué
□ Monitoring HTTPS configuré (uptime, expiration certificat)
```

---

## 🔧 COMMANDES UTILES

### Vérifier le mode actuel
```bash
docker compose exec web python /app/check_https_config.py
```

### Passer en mode production
```bash
# 1. Modifier .env
sed -i 's/PRODUCTION_MODE=0/PRODUCTION_MODE=1/g' .env

# 2. Redémarrer
docker compose down && docker compose up -d
```

### Passer en mode développement
```bash
# 1. Modifier .env
sed -i 's/PRODUCTION_MODE=1/PRODUCTION_MODE=0/g' .env

# 2. Redémarrer
docker compose down && docker compose up -d
```

### Tester HTTPS localement (avec certificat auto-signé)
```bash
# Générer un certificat auto-signé
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configurer Nginx local avec ce certificat
# ⚠️ Navigateur affichera un avertissement (normal en dev)
```

---

## 📚 RESSOURCES SUPPLÉMENTAIRES

### Documentation officielle
- Django Security: https://docs.djangoproject.com/en/5.0/topics/security/
- Let's Encrypt: https://letsencrypt.org/
- Mozilla SSL Config Generator: https://ssl-config.mozilla.org/

### Outils de test
- SSL Labs: https://www.ssllabs.com/ssltest/
- Security Headers: https://securityheaders.com/
- Observatory by Mozilla: https://observatory.mozilla.org/

### Best practices
- OWASP HTTPS: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html

---

## ✅ RÉSUMÉ FINAL

### Ce qui fonctionne MAINTENANT :

1. **En développement (localhost) :**
   - ✅ Site accessible en HTTP
   - ✅ Pas besoin de certificat SSL
   - ✅ Cookies fonctionnent normalement
   - ✅ Session 2 semaines
   - ✅ `PRODUCTION_MODE=0`

2. **En production (serveur réel) :**
   - ✅ Redirection automatique HTTP → HTTPS
   - ✅ Cookies sécurisés (HTTPS uniquement)
   - ✅ HSTS activé (1 an)
   - ✅ Session 1 heure
   - ✅ `PRODUCTION_MODE=1`

3. **Switch automatique :**
   - ✅ Basculement avec 1 seule variable d'environnement
   - ✅ Aucune modification de code
   - ✅ Déploiement simplifié

---

**🎉 HTTPS/SSL IMPLÉMENTÉ AVEC SUCCÈS !**

**Tu peux maintenant :**
- ✅ Développer en local sans problème
- ✅ Déployer en production avec HTTPS automatique
- ✅ Basculer entre les modes facilement

---

**Développé par l'expert sécurité AI pour SCINDONGO Immo** 🔒  
**Prêt pour la production !** 🚀
