#!/bin/sh
set -e

echo "🚀 Checking PostgreSQL readiness with psycopg2..."
python << 'PY'
import os
import time
import psycopg2
from psycopg2 import OperationalError

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
dbname = os.environ.get("POSTGRES_DB", "scindongo_immo")
user = os.environ.get("POSTGRES_USER", "postgres")
password = os.environ.get("POSTGRES_PASSWORD", "postgres")

for i in range(30):
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
        conn.close()
        print("✅ Database ready.")
        break
    except OperationalError as e:
        print(f"⏳ Waiting for database at {host}:{port}... ({i+1}/30)")
        time.sleep(2)
else:
    raise SystemExit("❌ Database unreachable")
PY

echo "🧩 Applying migrations..."
python manage.py migrate --noinput

echo "👤 Ensuring superuser exists..."
python manage.py shell << 'PY'
from django.contrib.auth import get_user_model

User = get_user_model()
email = "amadoubousso50@gmail.com"
password = "Admin123!"

user, created = User.objects.get_or_create(
    email=email,
    defaults={
        "is_staff": True,
        "is_superuser": True,
    },
)

if created:
    user.set_password(password)
    user.save()
    print("✅ Superuser created:")
else:
    print("ℹ️ Superuser already existed, password unchanged:")

print(f"   email: {email}")
print(f"   password: {password}")
PY

echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

echo "🔍 Detecting DJANGO_SETTINGS_MODULE from manage.py..."
export DJANGO_SETTINGS_MODULE=$(python << 'PY'
import re
from pathlib import Path

manage = Path("manage.py")
text = manage.read_text(encoding="utf-8")
m = re.search(r"DJANGO_SETTINGS_MODULE', '(.+?)'", text)
if m:
    print(m.group(1))
PY
)

if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
  echo "⚠️ Impossible de détecter DJANGO_SETTINGS_MODULE depuis manage.py."
  echo "   Fallback sur valeur par défaut: config.settings"
  export DJANGO_SETTINGS_MODULE="config.settings"
fi

echo "🔥 Starting Gunicorn with DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
exec gunicorn scindongo_immo.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3
