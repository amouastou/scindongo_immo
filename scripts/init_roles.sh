#!/bin/bash
set -euo pipefail

# Initialise les rôles CLIENT, COMMERCIAL, ADMIN via commande Django
cd "$(dirname "$0")"/..

docker-compose exec -T web python manage.py init_roles
