from django.core.management.base import BaseCommand
from accounts.models import Role

DEFAULT_ROLES = [
    ("CLIENT", "Client"),
    ("COMMERCIAL", "Commercial"),
    ("ADMIN", "Administrateur"),
]

class Command(BaseCommand):
    help = "Initialise les rôles de base (CLIENT, COMMERCIAL, ADMIN) s'ils n'existent pas"

    def handle(self, *args, **options):
        created = 0
        for code, libelle in DEFAULT_ROLES:
            obj, was_created = Role.objects.get_or_create(code=code, defaults={"libelle": libelle})
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"✓ Rôle créé: {code} - {libelle}"))
            else:
                # Mettre à jour libellé si vide
                if not obj.libelle:
                    obj.libelle = libelle
                    obj.save(update_fields=["libelle"])
                self.stdout.write(f"= Rôle déjà présent: {code} - {obj.libelle}")
        if created == 0:
            self.stdout.write(self.style.WARNING("Aucun nouveau rôle créé (déjà initialisés)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Terminé. {created} rôle(s) créé(s)."))
