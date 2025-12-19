import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'django_filters',
    'accounts',
    'core',
    'catalog',
    'sales',
    'api',
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Compression GZIP pour accélérer
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AuditMiddleware',
    'accounts.middleware.RateLimitMiddleware',  # Rate limiting personnalisé
]

ROOT_URLCONF = 'scindongo_immo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'scindongo_immo.wsgi.application'
ASGI_APPLICATION = 'scindongo_immo.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'scindongo_immo'),
        'USER': os.environ.get('POSTGRES_USER', 'scindongo'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'scindongo'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        # Optimisations de connexion PostgreSQL
        'CONN_MAX_AGE': 600,  # Réutilise les connexions pendant 10 minutes
        'OPTIONS': {
            'connect_timeout': 5,  # Timeout de connexion 5s
        },
    }
}

AUTH_USER_MODEL = 'accounts.User'

# URL de redirection pour login/logout
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==========================================
# CACHE CONFIGURATION - Redis for OTP System
# ==========================================
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'scindongo',
        'TIMEOUT': 300,  # Default timeout 5 minutes
    }
}

# OTP Configuration Constants
CONTRAT_OTP_EXPIRY = 300  # 5 minutes
CONTRAT_OTP_MAX_ATTEMPTS = 3
CONTRAT_OTP_BLOCK_DURATION = 900  # 15 minutes

# ==========================================
# LOCALIZATION
# ==========================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ==========================================
# SÉCURITÉ HTTPS/SSL - CONFIGURATION CONDITIONNELLE
# ==========================================
# En développement (localhost), HTTPS est désactivé
# En production, HTTPS est activé automatiquement
PRODUCTION_MODE = os.environ.get('PRODUCTION_MODE', '0') == '1'

if PRODUCTION_MODE:
    # === CONFIGURATION PRODUCTION : HTTPS ACTIVÉ ===
    print("🔒 MODE PRODUCTION : HTTPS/SSL activé")
    
    # Force HTTPS pour toutes les requêtes
    SECURE_SSL_REDIRECT = True
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookies sécurisés (HTTPS uniquement)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    
    # Session expire après 1 heure d'inactivité
    SESSION_COOKIE_AGE = 3600  # 1 heure
    SESSION_SAVE_EVERY_REQUEST = True  # Prolonge la session à chaque requête
    
    # Sécurité supplémentaire
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Proxy SSL (si derrière Nginx/Apache)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
else:
    # === CONFIGURATION DÉVELOPPEMENT : HTTPS DÉSACTIVÉ ===
    print("🔓 MODE DÉVELOPPEMENT : HTTPS/SSL désactivé (localhost)")
    
    # Pas de redirection HTTPS
    SECURE_SSL_REDIRECT = False
    
    # HSTS désactivé
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    
    # Cookies non sécurisés (HTTP autorisé)
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True  # Toujours activé (protection XSS)
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    
    # Session expire après 2 semaines (plus confortable en dev)
    SESSION_COOKIE_AGE = 1209600  # 2 semaines
    SESSION_SAVE_EVERY_REQUEST = False
    
    # Sécurité de base (même en dev)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'  # Moins strict en dev
    
    # Proxy SSL
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# File Upload Settings - Allow up to 60MB for large documents like brochures
DATA_UPLOAD_MAX_MEMORY_SIZE = 62914560  # 60MB in bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 62914560  # 60MB in bytes

# ----- PATCH ÉTAPE 6 -----
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# ==========================================
# EMAIL CONFIGURATION
# ==========================================
# Pour le développement, utiliser la console
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'  # Affiche dans la console
)

# Pour la production, configurez ces variables d'environnement :
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_TIMEOUT = 10  # Timeout SMTP en secondes (évite les blocages)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@scindongo.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# URL du site (pour les liens dans les emails)
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# ==========================================
# RATE LIMITING CONFIGURATION
# ==========================================
# django-ratelimit utilise le cache Django pour stocker les compteurs
# Clé pour identifier l'utilisateur : 'user' (si authentifié) ou 'ip' (sinon)
RATELIMIT_ENABLE = True  # Activer le rate limiting
RATELIMIT_USE_CACHE = 'default'  # Utilise le cache Redis

