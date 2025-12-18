# 📧 GUIDE : Configurer Gmail SMTP pour Envoi d'Emails Réels

## ✅ Corrections Apportées

### 1. **Bouton "Renvoyer" fonctionne correctement**
- ✅ Ne redirige plus vers login
- ✅ Reste sur la page `registration-pending`
- ✅ Demande l'email de l'utilisateur
- ✅ Accessible sans être connecté

### 2. **Message clair si compte non vérifié**
- ✅ À la connexion, si email pas vérifié → message d'erreur personnalisé
- ✅ Lien direct pour renvoyer l'email
- ✅ Redirection automatique vers page de vérification

### 3. **Email doit être envoyé en vrai (pas console)**

---

## 🚀 Configuration Gmail SMTP (Emails Réels)

### Étape 1 : Activer la Validation en 2 Étapes

1. Allez sur https://myaccount.google.com/security
2. Cliquez sur **"Validation en 2 étapes"**
3. Suivez les instructions pour activer

### Étape 2 : Créer un Mot de Passe d'Application

1. Allez sur https://myaccount.google.com/apppasswords
2. Sélectionnez **"Application" : Autre (nom personnalisé)**
3. Saisissez : `SCINDONGO Immo`
4. Cliquez sur **Générer**
5. **Copiez le mot de passe** (16 caractères sans espaces)
   - Exemple : `abcd efgh ijkl mnop` → Copier : `abcdefghijklmnop`

### Étape 3 : Créer/Modifier le fichier `.env`

```bash
cd /home/amanstou/SCINDONGO_IMMO_FINAL_UNIFIE
nano .env
```

Ajoutez ces lignes (remplacez avec vos vraies valeurs) :

```env
# Configuration Email Gmail SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=bussoam18@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
DEFAULT_FROM_EMAIL=noreply@scindongo.com
SITE_URL=http://localhost:8000
```

**⚠️ IMPORTANT :**
- Remplacez `bussoam18@gmail.com` par VOTRE email Gmail
- Remplacez `abcdefghijklmnop` par LE MOT DE PASSE D'APPLICATION (pas votre mot de passe Gmail !)

### Étape 4 : Redémarrer Docker

```bash
docker-compose down
docker-compose up --build
```

---

## 🧪 Test Complet

### Test 1 : Inscription
1. Accédez à http://localhost:8000/comptes/register/
2. Remplissez le formulaire avec un **vrai email** (le vôtre)
3. Cliquez sur **S'inscrire**
4. Vérifiez que vous êtes redirigé vers `/registration-pending/`

### Test 2 : Réception Email
1. Ouvrez votre boîte email
2. Cherchez un email de **"noreply@scindongo.com"**
3. Sujet : **"Vérifiez votre adresse email - SCINDONGO Immo"**
4. Si pas reçu : vérifiez **Spam/Courrier indésirable**

### Test 3 : Vérification
1. Ouvrez l'email
2. Cliquez sur le bouton **"Vérifier mon email"**
3. Vous devez être redirigé vers une page de confirmation
4. Un deuxième email de bienvenue doit arriver

### Test 4 : Connexion
1. Accédez à http://localhost:8000/comptes/login/
2. Saisissez votre email et mot de passe
3. Connexion doit fonctionner ✅

### Test 5 : Tentative connexion avant vérification
1. Créez un nouveau compte
2. N'ouvrez PAS l'email de vérification
3. Essayez de vous connecter
4. Vous devez voir : **"⚠️ Votre compte n'est pas encore activé..."**

### Test 6 : Renvoyer Email
1. Allez sur http://localhost:8000/comptes/registration-pending/
2. Saisissez votre email
3. Cliquez sur **"Renvoyer l'email de vérification"**
4. Vérifiez que vous restez sur la même page
5. Un nouvel email doit arriver

---

## ❌ Dépannage

### Problème : "SMTPAuthenticationError: Username and Password not accepted"

**Causes possibles :**
1. Mot de passe d'application incorrect
2. Validation en 2 étapes pas activée
3. Email incorrect dans EMAIL_HOST_USER

**Solutions :**
1. Regénérez un nouveau mot de passe d'application
2. Vérifiez que la validation en 2 étapes est activée
3. Vérifiez que EMAIL_HOST_USER = votre email Gmail complet

### Problème : "SMTPServerDisconnected: Connection unexpectedly closed"

**Cause :** Gmail bloque l'application

**Solutions :**
1. Allez sur https://myaccount.google.com/lesssecureapps
2. Ou utilisez SendGrid à la place (recommandé pour production)

### Problème : Email arrive dans Spam

**Cause :** Gmail considère l'email comme spam car DEFAULT_FROM_EMAIL != EMAIL_HOST_USER

**Solutions :**
1. Changez `DEFAULT_FROM_EMAIL=bussoam18@gmail.com` (même que EMAIL_HOST_USER)
2. Ou configurez SPF/DKIM pour votre domaine (production)

### Problème : "Connexion refusée" lors de l'envoi

**Vérifiez :**
```bash
docker-compose logs web | grep -i email
docker-compose logs web | grep -i smtp
```

---

## 🎯 Alternative Recommandée : SendGrid

Pour la production, SendGrid est plus fiable que Gmail.

### Avantages :
- ✅ 100 emails/jour gratuits
- ✅ Plus rapide et fiable
- ✅ Statistiques d'envoi
- ✅ Pas de risque de blocage

### Configuration SendGrid :

1. Créez un compte : https://signup.sendgrid.com/
2. Générez une clé API
3. Modifiez `.env` :

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.votre-clé-api-sendgrid
DEFAULT_FROM_EMAIL=noreply@scindongo.com
SITE_URL=http://localhost:8000
```

---

## 📊 Vérification en Base de Données

### Vérifier le statut des utilisateurs

```bash
docker-compose exec web python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Voir tous les utilisateurs
for user in User.objects.all():
    print(f"{user.email} | Vérifié: {user.email_verified} | Actif: {user.is_active}")

# Activer manuellement un utilisateur (pour dépannage)
user = User.objects.get(email='bussoam18@gmail.com')
user.email_verified = True
user.is_active = True
user.save()
print(f"✅ {user.email} activé manuellement")
```

### Voir les emails envoyés (console backend)

```bash
docker-compose logs web | grep -A 30 "Subject:"
```

---

## ✅ Checklist Finale

Avant de passer à la suite, vérifiez :

- [ ] Mot de passe d'application Gmail créé
- [ ] Fichier `.env` créé avec bonnes valeurs
- [ ] Docker redémarré (`docker-compose up --build`)
- [ ] Test inscription avec vrai email
- [ ] Email reçu dans boîte mail (ou spam)
- [ ] Lien de vérification cliqué
- [ ] Email de bienvenue reçu
- [ ] Connexion fonctionne après vérification
- [ ] Message clair si tentative connexion avant vérification
- [ ] Bouton "Renvoyer" fonctionne et reste sur page pending

---

## 🚀 Après Validation

Une fois que tout fonctionne :

1. **Sécuriser le `.env`** (ne jamais commit dans Git)
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Passer aux autres sécurités** :
   - Rate limiting (anti-bruteforce)
   - Headers HTTP sécurisés (HSTS, CSP, X-Frame-Options)
   - Protection CSRF renforcée
   - Monitoring des tentatives d'attaque

3. **Documentation Production** :
   - Configurer SendGrid pour production
   - Configurer domaine personnalisé
   - Configurer SPF/DKIM/DMARC

---

**Date :** 17 Décembre 2025  
**Status :** ✅ Prêt à tester avec Gmail SMTP
