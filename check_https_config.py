#!/usr/bin/env python3
"""
Script pour vérifier le mode HTTPS actuel
"""
import os
import sys

# Ajouter le projet au path
sys.path.insert(0, '/app')

# Charger Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scindongo_immo.settings')
import django
django.setup()

from django.conf import settings

print("\n" + "="*60)
print("🔍 VÉRIFICATION CONFIGURATION HTTPS/SSL")
print("="*60 + "\n")

# Mode de fonctionnement
production_mode = os.environ.get('PRODUCTION_MODE', '0') == '1'
print(f"Mode de fonctionnement: {'🔒 PRODUCTION' if production_mode else '🔓 DÉVELOPPEMENT'}")
print(f"PRODUCTION_MODE = {os.environ.get('PRODUCTION_MODE', '0')}\n")

# Configuration HTTPS
print("Configuration actuelle:")
print(f"  - SECURE_SSL_REDIRECT:         {settings.SECURE_SSL_REDIRECT}")
print(f"  - SECURE_HSTS_SECONDS:         {settings.SECURE_HSTS_SECONDS}")
print(f"  - SESSION_COOKIE_SECURE:       {settings.SESSION_COOKIE_SECURE}")
print(f"  - CSRF_COOKIE_SECURE:          {settings.CSRF_COOKIE_SECURE}")
print(f"  - SESSION_COOKIE_AGE:          {settings.SESSION_COOKIE_AGE} secondes ({settings.SESSION_COOKIE_AGE // 3600} heures)")
print(f"  - X_FRAME_OPTIONS:             {settings.X_FRAME_OPTIONS}")

print("\n" + "="*60)
if production_mode:
    print("✅ HTTPS/SSL ACTIVÉ - Mode Production")
    print("   → Redirection automatique HTTP → HTTPS")
    print("   → Cookies sécurisés (HTTPS uniquement)")
    print("   → HSTS activé (31536000 secondes = 1 an)")
    print("   → Session expire après 1 heure d'inactivité")
else:
    print("✅ HTTPS/SSL DÉSACTIVÉ - Mode Développement")
    print("   → Fonctionne en HTTP (localhost)")
    print("   → Cookies non sécurisés (compatible localhost)")
    print("   → HSTS désactivé")
    print("   → Session expire après 2 semaines")
print("="*60 + "\n")
