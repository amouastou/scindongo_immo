"""
Tests pour vérifier les permissions RBAC et validations métier.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from accounts.models import Role
from catalog.models import Programme, TypeBien, ModeleBien, Unite
from sales.models import Client, Reservation, Contrat, Paiement, BanquePartenaire, Financement, Echeance
from core.choices import (
    ProgrammeStatus, UniteStatus, ReservationStatus, ContratStatus,
    PaiementStatus, FinancementStatus, MoyenPaiement, UserRole
)


User = get_user_model()


class PermissionTestCase(APITestCase):
    """Tests pour les permissions RBAC."""

    def setUp(self):
        """Créer des utilisateurs avec différents rôles."""
        # Créer les rôles
        self.role_client = Role.objects.create(code="CLIENT", libelle="Client")
        self.role_commercial = Role.objects.create(code="COMMERCIAL", libelle="Commercial")
        self.role_admin = Role.objects.create(code="ADMIN", libelle="Admin")

        # Créer les utilisateurs
        self.user_client = User.objects.create_user(
            email="client@example.com",
            password="testpass123"
        )
        self.user_client.roles.add(self.role_client)

        self.user_commercial = User.objects.create_user(
            email="commercial@example.com",
            password="testpass123"
        )
        self.user_commercial.roles.add(self.role_commercial)

        self.user_admin = User.objects.create_user(
            email="admin@example.com",
            password="testpass123"
        )
        self.user_admin.roles.add(self.role_admin)

        # Créer un client profile
        self.client_profile = Client.objects.create(
            user=self.user_client,
            nom="Dupont",
            prenom="Jean",
            telephone="+221701234567",
            email="jean.dupont@example.com"
        )

        # Créer un programme, unité, réservation
        self.programme = Programme.objects.create(
            nom="Résidences Test",
            statut=ProgrammeStatus.ACTIF
        )

        self.type_bien = TypeBien.objects.create(
            code="APPT",
            libelle="Appartement"
        )

        self.modele_bien = ModeleBien.objects.create(
            type_bien=self.type_bien,
            nom_marketing="Appt T2",
            prix_base_ttc=50000000
        )

        self.unite = Unite.objects.create(
            programme=self.programme,
            modele_bien=self.modele_bien,
            reference_lot="A101",
            prix_ttc=50000000,
            statut_disponibilite=UniteStatus.DISPONIBLE
        )

        self.reservation = Reservation.objects.create(
            client=self.client_profile,
            unite=self.unite,
            acompte=5000000,
            statut=ReservationStatus.EN_COURS
        )

        self.client = APIClient()

    def test_client_can_see_own_reservations(self):
        """Test : Client voit ses propres réservations."""
        self.client.force_authenticate(user=self.user_client)
        response = self.client.get('/api/reservations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Doit contenir la réservation du client
        self.assertGreater(len(response.data['results']), 0)

    def test_client_cannot_see_other_reservations(self):
        """Test : Client ne peut pas voir les réservations d'autres clients."""
        # Créer un autre client
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        other_user.roles.add(self.role_client)
        other_client_profile = Client.objects.create(
            user=other_user,
            nom="Martin",
            prenom="Pierre",
            telephone="+221702345678",
            email="pierre.martin@example.com"
        )

        # Créer une réservation pour l'autre client
        other_reservation = Reservation.objects.create(
            client=other_client_profile,
            unite=self.unite,
            acompte=3000000,
            statut=ReservationStatus.EN_COURS
        )
        
        # Le premier client se connecte
        self.client.force_authenticate(user=self.user_client)
        response = self.client.get('/api/reservations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérifier que seule SA réservation est visible
        reservation_ids = [r['id'] for r in response.data['results']]
        self.assertIn(str(self.reservation.id), reservation_ids)
        self.assertNotIn(str(other_reservation.id), reservation_ids)

    def test_commercial_can_see_all_reservations(self):
        """Test : Commercial voit toutes les réservations."""
        self.client.force_authenticate(user=self.user_commercial)
        response = self.client.get('/api/reservations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_see_all_reservations(self):
        """Test : Admin voit toutes les réservations."""
        self.client.force_authenticate(user=self.user_admin)
        response = self.client.get('/api/reservations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ValidationTestCase(APITestCase):
    """Tests pour les validations métier."""

    def setUp(self):
        """Créer les objets de test."""
        # Rôles et users
        self.role_client = Role.objects.create(code="CLIENT", libelle="Client")
        self.role_commercial = Role.objects.create(code="COMMERCIAL", libelle="Commercial")

        self.user_client = User.objects.create_user(
            email="client@example.com",
            password="testpass123"
        )
        self.user_client.roles.add(self.role_client)

        self.user_commercial = User.objects.create_user(
            email="commercial@example.com",
            password="testpass123"
        )
        self.user_commercial.roles.add(self.role_commercial)

        # Client profile
        self.client_profile = Client.objects.create(
            user=self.user_client,
            nom="Dupont",
            prenom="Jean",
            telephone="+221701234567",
            email="jean.dupont@example.com"
        )

        # Programme, type, modèle, unité
        self.programme = Programme.objects.create(
            nom="Résidences Test",
            statut=ProgrammeStatus.ACTIF
        )

        self.type_bien = TypeBien.objects.create(
            code="APPT",
            libelle="Appartement"
        )

        self.modele_bien = ModeleBien.objects.create(
            type_bien=self.type_bien,
            nom_marketing="Appt T2",
            prix_base_ttc=50000000
        )

        self.unite = Unite.objects.create(
            programme=self.programme,
            modele_bien=self.modele_bien,
            reference_lot="A101",
            prix_ttc=50000000,
            statut_disponibilite=UniteStatus.DISPONIBLE
        )

        self.client_api = APIClient()

    def test_cannot_create_reservation_with_acompte_greater_than_price(self):
        """Test : Impossible de créer une réservation avec acompte > prix."""
        self.client_api.force_authenticate(user=self.user_commercial)
        
        data = {
            "client": self.client_profile.id,
            "unite": self.unite.id,
            "acompte": 60000000,  # > prix (50000000)
            "statut": ReservationStatus.EN_COURS
        }
        
        response = self.client_api.post('/api/reservations/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("acompte", response.data)

    def test_cannot_create_contrat_if_reservation_not_confirmed(self):
        """Test : Impossible de créer un contrat si la réservation n'est pas confirmée."""
        # Créer une réservation en_cours
        reservation = Reservation.objects.create(
            client=self.client_profile,
            unite=self.unite,
            acompte=5000000,
            statut=ReservationStatus.EN_COURS
        )

        self.client_api.force_authenticate(user=self.user_commercial)
        
        data = {
            "reservation": reservation.id,
            "numero": "CNT001",
            "statut": ContratStatus.BROUILLON
        }
        
        response = self.client_api.post('/api/contrats/', data)
        # Doit retourner une erreur de validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reserve_unite_after_reservation_created(self):
        """Test : L'unité passe en 'reserve' après création de réservation."""
        self.client_api.force_authenticate(user=self.user_commercial)
        
        self.assertEqual(self.unite.statut_disponibilite, UniteStatus.DISPONIBLE)
        
        # Créer une réservation
        data = {
            "client": self.client_profile.id,
            "unite": self.unite.id,
            "acompte": 5000000,
            "statut": ReservationStatus.EN_COURS
        }
        
        response = self.client_api.post('/api/reservations/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Vérifier que l'unité est maintenant 'reserve'
        self.unite.refresh_from_db()
        self.assertEqual(self.unite.statut_disponibilite, UniteStatus.RESERVE)


class AuthenticationTestCase(APITestCase):
    """Tests pour l'authentification."""

    def setUp(self):
        """Créer les objets de test."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.client_api = APIClient()

    def test_unauthenticated_cannot_access_protected_endpoints(self):
        """Test : Les utilisateurs non authentifiés ne peuvent pas accéder aux endpoints protégés."""
        response = self.client_api.get('/api/programmes/')
        # Dépend de la configuration - peut être 401 ou 403 selon les permissions
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_authenticated_user_can_access_programmes(self):
        """Test : Les utilisateurs authentifiés peuvent accéder à /api/programmes/."""
        self.client_api.force_authenticate(user=self.user)
        response = self.client_api.get('/api/programmes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
