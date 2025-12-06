#!/usr/bin/env python3
"""
Script pour recréer le programme RÉSIDENCES MAME DIARRA
selon le document fourni
"""
import os
import django
import sys
from pathlib import Path
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SECRET_KEY', 'temp-key')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scindongo_immo.settings')
django.setup()

from django.db import transaction
from django.core.files import File
from django.contrib.auth import get_user_model
from catalog.models import Programme, TypeBien, ModeleBien, Unite

User = get_user_model()

# Données extraites du document RÉSIDENCES MAME DIARRA.docx
MODELES_DATA = [
    {
        'nom_marketing': 'VILLA SALY - TYPE F3',
        'composition': '3 PIECES : 2 CHAMBRES - SALON',
        'pieces': {
            'Salon': 17.50,
            'Espace familial': 8.90,
            'Chambre Parents': 15.80,
            'Chambre 02': 11.55,
            'Cuisine': 7.40,
            'Salle de bain': 2.60,
            'Toilette': 2.60,
            'Dégagement': 5.75,
            'Porche': 1.60,
        },
        'surface_hab_m2': Decimal('73.70'),
        'prix_ttc': Decimal('25500000'),
        'image_illustration': 'image3.png',  # Image construite (pas le plan)
    },
    {
        'nom_marketing': 'VILLA SALY - TYPE F3 AMELIOREE',
        'composition': '3 PIECES : 2 CHAMBRES - SALON',
        'pieces': {
            'Salon': 17.50,
            'Espace familial': 8.90,
            'Chambre Parents': 15.80,
            'Chambre 02': 11.55,
            'Cuisine': 7.40,
            'Salle de bain': 2.60,
            'Toilette': 2.60,
            'Dégagement': 5.75,
            'Porche': 1.60,
            'Escaliers': 7.55,
        },
        'surface_hab_m2': Decimal('81.25'),
        'prix_ttc': Decimal('26500000'),
        'image_illustration': 'image2.png',
    },
    {
        'nom_marketing': 'VILLA SALY - TYPE F3 AMELIOREE (3 Chambres)',
        'composition': '4 PIECES : 3 CHAMBRES - SALON',
        'pieces': {
            'Salon': 17.50,
            'Espace familial': 8.90,
            'Chambre Parents': 15.80,
            'Chambre 02': 11.55,
            'Chambre 03': 11.55,
            'Cuisine': 7.40,
            'Salle de bain': 2.60,
            'Toilette': 2.60,
            'Dégagement': 5.75,
            'Porche': 1.60,
        },
        'surface_hab_m2': Decimal('85.25'),
        'prix_ttc': Decimal('29500000'),
        'image_illustration': 'image4.png',
    },
    {
        'nom_marketing': 'VILLA AICHA - TYPE F4',
        'composition': '4 PIECES : 3 CHAMBRES - SALON',
        'pieces': {
            'Salon': 17.50,
            'Espace familial': 8.90,
            'Chambre Parents': 15.80,
            'Chambre 02': 11.55,
            'Chambre 03': 11.55,
            'Cuisine': 7.40,
            'Salle de bain': 2.60,
            'Toilette': 2.60,
            'Dégagement': 5.75,
            'Porche': 1.60,
            'Escaliers': 7.55,
        },
        'surface_hab_m2': Decimal('92.80'),
        'prix_ttc': Decimal('30500000'),
        'image_illustration': 'image6.png',
    },
    {
        'nom_marketing': 'VILLA FATIMA - TYPE F5 (RDC + Etage)',
        'composition': 'F5 - RDC + 01 ETAGE',
        'pieces': {
            'RDC - Séjour': 30.45,
            'RDC - Chambre 01': 10.50,
            'RDC - Cuisine': 7.90,
            'RDC - Toilette': 3.00,
            'RDC - Terrasse 01': 6.20,
            'RDC - Terrasse 02': 3.40,
            'RDC - Surface': 74.45,
            'Etage - Chambre 02': 15.75,
            'Etage - Chambre 03': 12.15,
            'Etage - Chambre 04': 10.50,
            'Etage - Salle de bain 02': 4.15,
            'Etage - Salle de bain 03': 3.70,
            'Etage - Salle de bain 04': 3.00,
            'Etage - Dressing': 4.15,
            'Etage - Balcon 01': 6.20,
            'Etage - Balcon 02': 2.10,
            'Etage - Surface': 73.05,
        },
        'surface_hab_m2': Decimal('147.50'),  # 74.45 + 73.05
        'prix_ttc': Decimal('49500000'),
        'image_illustration': 'image7.png',
    },
]


def main():
    print("🏗️  RECRÉATION DU PROGRAMME RÉSIDENCES MAME DIARRA")
    print("=" * 70)
    
    with transaction.atomic():
        # 1. Récupérer la commerciale existante
        try:
            commercial = User.objects.get(email='mamefatou@gmail.com')
            print(f"✅ Commerciale: {commercial.get_full_name()}")
        except User.DoesNotExist:
            print("❌ Commerciale mamefatou@gmail.com non trouvée")
            sys.exit(1)
        
        # 2. Créer le Programme
        programme = Programme.objects.create(
            nom='RÉSIDENCES MAME DIARRA',
            description='''Programme résidentiel à Bayakh avec 5 modèles de villas disponibles.
Finitions de qualité, quartier en développement.''',
            adresse='Sacré Coeur 1 Immeuble D TRANSVEES 5 et 6',
            statut='actif',
            notaire_nom='ETUDES MAITRE ABDEL KADER NIANG',
            notaire_contact='33 951 07 58',
            contact_commercial=commercial,
        )
        
        # Ajouter image principale
        img_principale = Path('media/programmes/mame_diarra/image1.jpg')
        if img_principale.exists():
            with open(img_principale, 'rb') as f:
                programme.image_principale.save('mame_diarra_principal.jpg', File(f), save=True)
        
        print(f"✅ Programme créé: {programme.nom}")
        
        # 3. Créer TypeBien IMMEUBLE (biens bâtis, pas terrain nu)
        type_immeuble, created = TypeBien.objects.get_or_create(
            code='IMMEUBLE',
            defaults={'libelle': 'Immeuble / Bien bâti'}
        )
        print(f"✅ TypeBien: {type_immeuble.code}")
        
        # 4. Créer les 5 modèles et leurs unités
        print(f"\n📐 Création des modèles et unités:")
        print("-" * 70)
        
        for i, data in enumerate(MODELES_DATA, 1):
            # Créer le modèle
            modele = ModeleBien.objects.create(
                type_bien=type_immeuble,
                nom_marketing=data['nom_marketing'],
                surface_hab_m2=data['surface_hab_m2'],
                prix_base_ttc=data['prix_ttc'],
                description=data['composition'],
            )
            print(f"{i}. Modèle: {modele.nom_marketing}")
            print(f"   Surface: {modele.surface_hab_m2} m²")
            print(f"   Prix: {int(modele.prix_base_ttc):,} FCFA")
            
            # Créer UNE unité par modèle
            # Référence unique basée sur le nom complet pour éviter duplications
            ref_lot = f"MD-{i:02d}-{data['nom_marketing'].replace(' ', '_')[:25]}"
            unite = Unite.objects.create(
                programme=programme,
                modele_bien=modele,
                reference_lot=ref_lot,
                prix_ttc=data['prix_ttc'],
                statut_disponibilite='disponible',
                caracteristiques=data['pieces'],  # JSON avec détails pièces
            )
            
            # Ajouter image d'illustration (image construite, pas le plan)
            img_file = Path(f"media/programmes/mame_diarra/{data['image_illustration']}")
            if img_file.exists():
                with open(img_file, 'rb') as f:
                    unite.image.save(data['image_illustration'], File(f), save=True)
                print(f"   📷 Image: {data['image_illustration']}")
            
            print(f"   ✅ Unité: {unite.reference_lot}\n")
        
        # 5. Résumé
        print("=" * 70)
        print("✅ RECRÉATION TERMINÉE")
        print(f"📊 Programme: {programme.nom}")
        print(f"📊 Commerciale: {commercial.get_full_name()}")
        print(f"📊 Modèles: {ModeleBien.objects.filter(type_bien=type_immeuble).count()}")
        print(f"📊 Unités: {Unite.objects.filter(programme=programme).count()}")
        print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
