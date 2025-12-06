"""
Tests pour la gestion des chantiers par unité.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import User, Role
from catalog.models import Programme, TypeBien, ModeleBien, Unite, AvancementChantierUnite, PhotoChantierUnite
from sales.models import Client, Reservation
from core.choices import ContratStatus, UniteStatus, ReservationStatus
from decimal import Decimal
from datetime import datetime, date


class AvancementChantierUniteAPITests(APITestCase):
    """Tests pour l'API d'avancement chantier par unité."""
    
    def setUp(self):
        """Setup pour les tests."""
        # Créer les rôles
        admin_role, _ = Role.objects.get_or_create(code="ADMIN", defaults={"libelle": "Admin"})
        commercial_role, _ = Role.objects.get_or_create(code="COMMERCIAL", defaults={"libelle": "Commercial"})
        client_role, _ = Role.objects.get_or_create(code="CLIENT", defaults={"libelle": "Client"})
        
        # Créer les utilisateurs
        self.commercial_user = User.objects.create_user(
            email='commercial@example.com',
            password='pass123'
        )
        self.commercial_user.roles.add(commercial_role)
        
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='pass123'
        )
        self.client_user.roles.add(client_role)
        
        # Créer le profil client
        self.client_profile = Client.objects.create(
            user=self.client_user,
            nom='Dupont',
            prenom='Jean',
            telephone='777001234',
            email='client@example.com'
        )
        
        # Créer un programme
        self.programme = Programme.objects.create(
            nom='Test Programme',
            adresse='Test Address',
            statut='actif'
        )
        
        # Créer un type et modèle
        type_bien = TypeBien.objects.create(code='VILLA', libelle='Villa')
        self.modele = ModeleBien.objects.create(
            type_bien=type_bien,
            nom_marketing='Villa Test',
            prix_base_ttc=Decimal('50000000')
        )
        
        # Créer une unité
        self.unite = Unite.objects.create(
            programme=self.programme,
            modele_bien=self.modele,
            reference_lot='LOT-001',
            prix_ttc=Decimal('50000000'),
            statut_disponibilite='reserve'
        )
        
        # Créer une réservation avec contrat signé
        self.reservation = Reservation.objects.create(
            client=self.client_profile,
            unite=self.unite,
            statut=ReservationStatus.CONFIRMEE,
            acompte=Decimal('5000000')
        )
        
        # Créer un contrat signé
        from sales.models import Contrat
        self.contrat = Contrat.objects.create(
            reservation=self.reservation,
            numero='CONTRAT-001',
            statut=ContratStatus.SIGNE
        )
        
        self.client = APIClient()
    
    def test_commercial_can_create_avancement(self):
        """Commercial peut créer un avancement."""
        self.client.force_authenticate(user=self.commercial_user)
        
        url = reverse('avancement-unite-list')
        data = {
            'unite': self.unite.pk,
            'reservation': self.reservation.pk,
            'etape': 'Fondations',
            'date_pointage': date.today(),
            'pourcentage': 50,
            'commentaire': 'Test'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_client_cannot_create_avancement(self):
        """Client ne peut pas créer un avancement."""
        self.client.force_authenticate(user=self.client_user)
        
        url = reverse('avancement-unite-list')
        data = {
            'unite': self.unite.pk,
            'etape': 'Fondations',
            'date_pointage': date.today(),
            'pourcentage': 50,
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_client_can_read_own_avancements(self):
        """Client peut voir ses propres avancements."""
        # Créer un avancement
        AvancementChantierUnite.objects.create(
            unite=self.unite,
            reservation=self.reservation,
            etape='Fondations',
            date_pointage=date.today(),
            pourcentage=50
        )
        
        self.client.force_authenticate(user=self.client_user)
        url = reverse('avancement-unite-list')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_validation_pourcentage(self):
        """Validation du pourcentage (0-100)."""
        self.client.force_authenticate(user=self.commercial_user)
        
        url = reverse('avancement-unite-list')
        data = {
            'unite': self.unite.pk,
            'etape': 'Fondations',
            'date_pointage': date.today(),
            'pourcentage': 150,  # Invalid
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AvancementChantierUniteViewsTests(TestCase):
    """Tests pour les vues Django."""
    
    def setUp(self):
        """Setup pour les tests."""
        commercial_role, _ = Role.objects.get_or_create(code="COMMERCIAL")
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='pass123'
        )
        self.user.roles.add(commercial_role)
        
        # Créer programme, type, modèle, unité
        type_bien = TypeBien.objects.create(code='VILLA', libelle='Villa')
        programme = Programme.objects.create(nom='Test')
        modele = ModeleBien.objects.create(
            type_bien=type_bien,
            nom_marketing='Villa',
            prix_base_ttc=50000000
        )
        self.unite = Unite.objects.create(
            programme=programme,
            modele_bien=modele,
            reference_lot='LOT-001',
            prix_ttc=50000000,
            statut_disponibilite='reserve'
        )
    
    def test_chantiers_list_view_requires_login(self):
        """Vue liste chantiers nécessite login."""
        response = self.client.get(reverse('chantiers_unites_list'))
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_chantiers_list_view_requires_commercial(self):
        """Vue liste chantiers nécessite rôle commercial."""
        # Créer user client
        client_role, _ = Role.objects.get_or_create(code="CLIENT")
        client_user = User.objects.create_user(
            email='client@example.com',
            password='pass123'
        )
        client_user.roles.add(client_role)
        
        self.client.login(email='client@example.com', password='pass123')
        response = self.client.get(reverse('chantiers_unites_list'))
        self.assertEqual(response.status_code, 403)  # Permission denied
    
    def test_chantiers_list_view_for_commercial(self):
        """Commercial peut voir la liste des chantiers."""
        self.client.login(email='test@example.com', password='pass123')
        response = self.client.get(reverse('chantiers_unites_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestion des Chantiers')
