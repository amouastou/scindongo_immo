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

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SECRET_KEY', 'temp-key-for-import')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scindongo_immo.settings')
django.setup()

from catalog.models import Programme, TypeBien, ModeleBien, Unite
from django.core.files import File
from django.db import transaction


def import_programme():
    """Importe le programme RÉSIDENCES MAME DIARRA"""
    
    print("🏗️  Import du programme RÉSIDENCES MAME DIARRA")
    print("=" * 60)
    
    with transaction.atomic():
        # 1. Créer le Programme
        programme, created = Programme.objects.get_or_create(
            nom="RÉSIDENCES MAME DIARRA",
            defaults={
                'adresse': 'Bayakh, Dakar',
                'description': '''Programme résidentiel de standing à Bayakh.
Résidences modernes avec finitions de qualité, dans un quartier en plein développement.
Cinq modèles de villas disponibles: F3, F3 Améliorée, F4, F4 Améliorée et F5 duplex.
Idéal pour familles souhaitant allier confort et accessibilité.''',
                'date_livraison_prevue': '2025-12-31',
                'statut': 'actif',
                'notaire_nom': 'ETUDES MAITRE ABDEL KADER NIANG',
                'notaire_contact': '33 951 07 58',
            }
        )
        
        if created:
            print(f"✅ Programme créé: {programme.nom}")
            
            # Associer image principale si disponible
            main_image = Path("media/programmes/mame_diarra/image1.jpg")
            if main_image.exists():
                with open(main_image, 'rb') as f:
                    programme.image_principale.save('mame_diarra_main.jpg', File(f), save=True)
                print(f"   📷 Image principale ajoutée")
        else:
            print(f"ℹ️  Programme existe déjà: {programme.nom}")
        
        # 2. Créer les TypeBien (si nécessaire)
        type_villa, _ = TypeBien.objects.get_or_create(
            code="VILLA",
            defaults={'libelle': 'Villa / Maison individuelle'}
        )
        
        # 3. Créer les 5 modèles de villas
        modeles_data = [
            {
                'nom_marketing': 'VILLA SALY - TYPE F3',
                'type_bien': type_villa,
                'surface_hab_m2': Decimal('73.70'),
                'prix_base_ttc': Decimal('25500000'),
                'description': '''Villa plain-pied avec 2 chambres.
Surface habitable: 73,70 m²
Comprend: Salon (17,5 m²), Espace familial (8,9 m²), 2 chambres (15,8 + 11,55 m²), Cuisine (7,4 m²), Salle de bain, Toilette, Dégagement, Porche.''',
                'image_path': 'image3.png'
            },
            {
                'nom_marketing': 'VILLA SALY - TYPE F3 AMELIOREE',
                'type_bien': type_villa,
                'surface_hab_m2': Decimal('81.25'),
                'prix_base_ttc': Decimal('26500000'),
                'description': '''Villa plain-pied avec 2 chambres et étage accessible.
Surface habitable: 81,25 m²
Comprend escaliers (7,55 m²) pour possibilité d'extension future.''',
                'image_path': 'image2.png'
            },
            {
                'nom_marketing': 'VILLA SALY - TYPE F3 AMELIOREE (3 Chambres)',
                'type_bien': type_villa,
                'surface_hab_m2': Decimal('85.25'),
                'prix_base_ttc': Decimal('29500000'),
                'description': '''Villa plain-pied avec 3 chambres.
Surface habitable: 85,25 m²
Comprend: Salon, Espace familial, 3 chambres (15,8 + 11,55 + 11,55 m²), Cuisine, Salle de bain, Toilette, Dégagement, Porche.''',
                'image_path': 'image4.png'
            },
            {
                'nom_marketing': 'VILLA AICHA - TYPE F4',
                'type_bien': type_villa,
                'surface_hab_m2': Decimal('92.80'),
                'prix_base_ttc': Decimal('30500000'),
                'description': '''Villa plain-pied avec 3 chambres et escaliers.
Surface habitable: 92,80 m²
Comprend: Salon (17,5 m²), Espace familial (8,9 m²), 3 chambres (15,8 + 11,55 + 11,55 m²), Cuisine (7,4 m²), Salle de bain, Toilette, Dégagement, Porche, Escaliers (7,55 m²).''',
                'image_path': 'image6.png'
            },
            {
                'nom_marketing': 'VILLA FATIMA - TYPE F5 (RDC + Etage)',
                'type_bien': type_villa,
                'surface_hab_m2': Decimal('147.50'),  # 74.45 + 73.05
                'prix_base_ttc': Decimal('49500000'),
                'description': '''Villa duplex avec 4 chambres.
Surface habitable totale: 147,50 m² (RDC: 74,45 m² + Etage: 73,05 m²)
RDC: Séjour (30,45 m²), 1 chambre, Cuisine, Toilette, 2 terrasses.
Etage: 3 chambres avec 3 salles de bain, Dressing, 2 balcons.''',
                'image_path': 'image7.png'
            },
        ]
        
        modeles_created = []
        for data in modeles_data:
            image_path = data.pop('image_path')
            modele, created = ModeleBien.objects.get_or_create(
                type_bien=type_villa,
                nom_marketing=data['nom_marketing'],
                defaults=data
            )
            
            if created:
                print(f"✅ Modèle créé: {modele.nom_marketing} - {modele.surface_hab_m2} m² - {modele.prix_base_ttc:,} FCFA")
                
                # Note: Les images plan peuvent être ajoutées manuellement via l'admin Django
                # car ModeleBien n'a pas de champ image_plan dans le modèle actuel
                
                modeles_created.append(modele)
            else:
                print(f"ℹ️  Modèle existe déjà: {modele.nom_marketing}")
                modeles_created.append(modele)
        
        # 4. Créer les unités (lots) disponibles
        print("\n🏘️  Création des unités disponibles...")
        unites_count = 0
        
        for modele in modeles_created:
            # Créer 8 unités par modèle
            for i in range(1, 9):
                lot_numero = f"LOT-{modele.nom_marketing[:10].replace(' ', '')}-{i:02d}"
                
                unite, created = Unite.objects.get_or_create(
                    programme=programme,
                    reference_lot=lot_numero,
                    defaults={
                        'modele_bien': modele,
                        'prix_ttc': modele.prix_base_ttc,
                        'statut_disponibilite': 'disponible',
                    }
                )
                
                if created:
                    unites_count += 1
        
        print(f"✅ {unites_count} unités créées")
        
        # 5. Résumé
        print("\n" + "=" * 60)
        print("✅ IMPORT TERMINÉ AVEC SUCCÈS")
        print(f"📊 Programme: {programme.nom}")
        print(f"📊 Modèles: {len(modeles_created)}")
        print(f"📊 Unités disponibles: {unites_count}")
        print(f"📊 Total lots dans programme: {Unite.objects.filter(programme=programme).count()}")
        print("=" * 60)


if __name__ == '__main__':
    try:
        import_programme()
    except Exception as e:
        print(f"❌ Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
