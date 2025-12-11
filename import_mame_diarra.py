#!/usr/bin/env python3
"""
Script d'import du programme RÉSIDENCES MAME DIARRA
Sans suppression des données existantes
"""

import os
import django
import sys
from pathlib import Path
from decimal import Decimal
        modeles_data = [
            {
                'nom_marketing': 'VILLA SALY - TYPE F3',
                'type_bien': type_villa,
                'surface_hab_m2': Decimal('73.70'),
                'prix_unitaire': Decimal('25500000'),
                'description': '''Villa plain-pied avec 2 chambres.
from catalog.models import Programme, TypeBien, ModeleBien, Unite
#!/usr/bin/env python3
"""Script d'import du programme RÉSIDENCES MAME DIARRA (sans suppression)."""

import os
import sys
from decimal import Decimal
from pathlib import Path

import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SECRET_KEY", "temp-key-for-import")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scindongo_immo.settings")
django.setup()

from django.core.files import File  # noqa: E402
from django.db import transaction  # noqa: E402

from catalog.models import ModeleBien, Programme, TypeBien, Unite  # noqa: E402


def import_programme():
    print("🏗️  Import du programme RÉSIDENCES MAME DIARRA")
    print("=" * 60)

    with transaction.atomic():
        programme, created = Programme.objects.get_or_create(
            nom="RÉSIDENCES MAME DIARRA",
            defaults={
                "adresse": "Bayakh, Dakar",
                "description": """Programme résidentiel de standing à Bayakh.
Résidences modernes avec finitions de qualité, dans un quartier en plein développement.
Cinq modèles de villas disponibles: F3, F3 Améliorée, F4, F4 Améliorée et F5 duplex.
Idéal pour familles souhaitant allier confort et accessibilité.""",
                "date_livraison_prevue": "2025-12-31",
                "statut": "actif",
                "notaire_nom": "ETUDES MAITRE ABDEL KADER NIANG",
                "notaire_contact": "33 951 07 58",
            },
        )

        if created:
            print(f"✅ Programme créé: {programme.nom}")
            main_image = Path("media/programmes/mame_diarra/image1.jpg")
            if main_image.exists():
                with open(main_image, "rb") as f:
                    programme.image_principale.save("mame_diarra_main.jpg", File(f), save=True)
                print("   📷 Image principale ajoutée")
        else:
            print(f"ℹ️  Programme existe déjà: {programme.nom}")

        type_villa, _ = TypeBien.objects.get_or_create(
            code="VILLA",
            defaults={"libelle": "Villa / Maison individuelle"},
        )

        modeles_data = [
            {
                "nom_marketing": "VILLA SALY - TYPE F3",
                "surface_hab_m2": Decimal("73.70"),
                "prix_unitaire": Decimal("25500000"),
                "description": """Villa plain-pied avec 2 chambres.
Surface habitable: 73,70 m²
Comprend: Salon (17,5 m²), Espace familial (8,9 m²), 2 chambres (15,8 + 11,55 m²), Cuisine (7,4 m²), Salle de bain, Toilette, Dégagement, Porche.""",
            },
            {
                "nom_marketing": "VILLA SALY - TYPE F3 AMELIOREE",
                "surface_hab_m2": Decimal("81.25"),
                "prix_unitaire": Decimal("26500000"),
                "description": """Villa plain-pied avec 2 chambres et étage accessible.
Surface habitable: 81,25 m²
Comprend escaliers (7,55 m²) pour possibilité d'extension future.""",
            },
            {
                "nom_marketing": "VILLA SALY - TYPE F3 AMELIOREE (3 Chambres)",
                "surface_hab_m2": Decimal("85.25"),
                "prix_unitaire": Decimal("29500000"),
                "description": """Villa plain-pied avec 3 chambres.
Surface habitable: 85,25 m²
Comprend: Salon, Espace familial, 3 chambres (15,8 + 11,55 + 11,55 m²), Cuisine, Salle de bain, Toilette, Dégagement, Porche.""",
            },
            {
                "nom_marketing": "VILLA AICHA - TYPE F4",
                "surface_hab_m2": Decimal("92.80"),
                "prix_unitaire": Decimal("30500000"),
                "description": """Villa plain-pied avec 3 chambres et escaliers.
Surface habitable: 92,80 m²
Comprend: Salon (17,5 m²), Espace familial (8,9 m²), 3 chambres (15,8 + 11,55 + 11,55 m²), Cuisine (7,4 m²), Salle de bain, Toilette, Dégagement, Porche, Escaliers (7,55 m²).""",
            },
            {
                "nom_marketing": "VILLA FATIMA - TYPE F5 (RDC + Etage)",
                "surface_hab_m2": Decimal("147.50"),
                "prix_unitaire": Decimal("49500000"),
                "description": """Villa duplex avec 4 chambres.
Surface habitable totale: 147,50 m² (RDC: 74,45 m² + Etage: 73,05 m²)
RDC: Séjour (30,45 m²), 1 chambre, Cuisine, Toilette, 2 terrasses.
Etage: 3 chambres avec 3 salles de bain, Dressing, 2 balcons.""",
            },
        ]

        modeles_created = []
        for data in modeles_data:
            prix_unitaire = data["prix_unitaire"]
            defaults = {
                "surface_hab_m2": data["surface_hab_m2"],
                "description": data["description"],
            }
            modele, created = ModeleBien.objects.get_or_create(
                type_bien=type_villa,
                nom_marketing=data["nom_marketing"],
                defaults=defaults,
            )
            if created:
                print(
                    f"✅ Modèle créé: {modele.nom_marketing} - {modele.surface_hab_m2} m² - {prix_unitaire:,} FCFA (prix indicatif)"
                )
            else:
                print(f"ℹ️  Modèle existe déjà: {modele.nom_marketing}")
                ModeleBien.objects.filter(pk=modele.pk).update(**defaults)

            modeles_created.append({"modele": modele, "prix_unitaire": prix_unitaire})

        print("\n🏘️  Création des unités disponibles...")
        unites_count = 0
        for modele_entry in modeles_created:
            modele = modele_entry["modele"]
            prix_unitaire = modele_entry["prix_unitaire"]
            for i in range(1, 9):
                lot_numero = f"LOT-{modele.nom_marketing[:10].replace(' ', '')}-{i:02d}"
                unite, created = Unite.objects.get_or_create(
                    programme=programme,
                    reference_lot=lot_numero,
                    defaults={
                        "modele_bien": modele,
                        "prix_ttc": prix_unitaire,
                        "statut_disponibilite": "disponible",
                    },
                )
                if created:
                    unites_count += 1

        print(f"✅ {unites_count} unités créées")
        print("\n" + "=" * 60)
        print("✅ IMPORT TERMINÉ AVEC SUCCÈS")
        print(f"📊 Programme: {programme.nom}")
        print(f"📊 Modèles: {len(modeles_created)}")
        print(f"📊 Unités disponibles: {unites_count}")
        print(f"📊 Total lots dans programme: {Unite.objects.filter(programme=programme).count()}")
        print("=" * 60)


if __name__ == "__main__":
    try:
        import_programme()
    except Exception as exc:  # pragma: no cover - script utility
        print(f"❌ Erreur lors de l'import: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

