"""
Tests automatisés pour la fusion - SCINDONGO Immo
Exécutez avec: python manage.py test tests.test_suite
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from accounts.models import User as CustomUser, Role
from catalog.models import Programme, Unite, ModeleBien, TypeBien
from sales.models import (
    Client, Reservation, Paiement, EcheanceLoyer, 
    Contrat, Financement, BanquePartenaire
)
from core.choices import (
    PaiementStatus, PaiementType, UniteStatus, 
    OperationType, ReservationStatus, ContratStatus
)


class TestDataFactory:
    """Factory pour créer les données de test"""
    
    @staticmethod
    def create_test_user(email, password='test123', role_code='CLIENT'):
        """Créer un utilisateur avec rôle"""
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name='Test',
            last_name='User'
        )
        role, _ = Role.objects.get_or_create(code=role_code)
        user.roles.add(role)
        return user

    @staticmethod
    def create_programme(nom, type_operation='LOCATION'):
        """Créer un programme test"""
        user = CustomUser.objects.create_user(
            email=f'commercial_{type_operation}@test.com',
            password='test123'
        )
        return Programme.objects.create(
            nom=nom,
            description=f'Test {type_operation}',
            type_operation=type_operation,
            contact_commercial=user,
            statut='actif'
        )

    @staticmethod
    def create_unite(programme, reference_lot='TEST-LOT-01', prix_ttc=1000000):
        """Créer une unité"""
        type_bien = TypeBien.objects.get_or_create(nom='F3')[0]
        modele = ModeleBien.objects.create(
            type_bien=type_bien,
            nom_marketing='Modèle Test',
            prix_base_ttc=prix_ttc
        )
        return Unite.objects.create(
            programme=programme,
            reference_lot=reference_lot,
            modele_bien=modele,
            prix_ttc=prix_ttc,
            statut_disponibilite='disponible'
        )

    @staticmethod
    def create_client(user):
        """Créer un profil client"""
        return Client.objects.create(
            user=user,
            nom=user.last_name,
            prenom=user.first_name,
            email=user.email,
            telephone='221701234567'
        )

    @staticmethod
    def create_reservation(client, unite):
        """Créer une réservation"""
        return Reservation.objects.create(
            client=client,
            unite=unite,
            date_reservation=date.today(),
            statut='en_cours'
        )


# =============================================================================
# TESTS MODÈLES
# =============================================================================

class ReservationModelTest(TestCase):
    """Tests pour le modèle Reservation"""
    
    def setUp(self):
        self.programme_location = TestDataFactory.create_programme('Test Location', 'LOCATION')
        self.programme_vente = TestDataFactory.create_programme('Test Vente', 'VENTE')
        
        self.unite_location = TestDataFactory.create_unite(self.programme_location, 'LOC-001')
        self.unite_vente = TestDataFactory.create_unite(self.programme_vente, 'VENTE-001')
        
        self.user = TestDataFactory.create_test_user('client@test.com', role_code='CLIENT')
        self.client = TestDataFactory.create_client(self.user)
        
        self.res_location = TestDataFactory.create_reservation(self.client, self.unite_location)
        self.res_vente = TestDataFactory.create_reservation(self.client, self.unite_vente)
    
    def test_is_location(self):
        """Test que is_location() retourne True pour LOCATION"""
        self.assertTrue(self.res_location.is_location())
        self.assertFalse(self.res_vente.is_location())
    
    def test_is_vente(self):
        """Test que is_vente() retourne True pour VENTE"""
        self.assertFalse(self.res_location.is_vente())
        self.assertTrue(self.res_vente.is_vente())
    
    def test_has_caution_payment_false_initially(self):
        """Initialement, aucun paiement de caution"""
        self.assertFalse(self.res_location.has_caution_payment())
    
    def test_has_caution_payment_after_creation(self):
        """Après création paiement de caution, retourne True"""
        Paiement.objects.create(
            reservation=self.res_location,
            montant=2000000,
            moyen='virement',
            source='test',
            type_paiement=PaiementType.CAUTION,
            statut=PaiementStatus.VALIDE
        )
        self.assertTrue(self.res_location.has_caution_payment())


class EcheanceModelTest(TestCase):
    """Tests pour le modèle EcheanceLoyer"""
    
    def setUp(self):
        self.programme = TestDataFactory.create_programme('Test', 'LOCATION')
        self.unite = TestDataFactory.create_unite(self.programme)
        self.user = TestDataFactory.create_test_user('client@test.com', role_code='CLIENT')
        self.client = TestDataFactory.create_client(self.user)
        self.reservation = TestDataFactory.create_reservation(self.client, self.unite)
    
    def test_is_payee_false(self):
        """Échéance non payée retourne False"""
        echeance = EcheanceLoyer.objects.create(
            reservation=self.reservation,
            numero_mois=1,
            montant=1000000,
            date_echeance=date.today() + timedelta(days=30),
            statut_paiement=PaiementStatus.ENREGISTRE
        )
        self.assertFalse(echeance.is_payee())
    
    def test_is_payee_true(self):
        """Échéance payée retourne True"""
        echeance = EcheanceLoyer.objects.create(
            reservation=self.reservation,
            numero_mois=1,
            montant=1000000,
            date_echeance=date.today() + timedelta(days=30),
            statut_paiement=PaiementStatus.VALIDE
        )
        self.assertTrue(echeance.is_payee())
    
    def test_is_en_retard_false(self):
        """Échéance future retourne is_en_retard=False"""
        echeance = EcheanceLoyer.objects.create(
            reservation=self.reservation,
            numero_mois=1,
            montant=1000000,
            date_echeance=date.today() + timedelta(days=30),
            statut_paiement=PaiementStatus.ENREGISTRE
        )
        self.assertFalse(echeance.is_en_retard())
    
    def test_is_en_retard_true(self):
        """Échéance écheue et non payée retourne True"""
        echeance = EcheanceLoyer.objects.create(
            reservation=self.reservation,
            numero_mois=1,
            montant=1000000,
            date_echeance=date.today() - timedelta(days=5),
            statut_paiement=PaiementStatus.ENREGISTRE
        )
        self.assertTrue(echeance.is_en_retard())


# =============================================================================
# TESTS VUES - COMMERCIAL PAYMENT VALIDATE
# =============================================================================

class CommercialPaymentValidateViewTest(TestCase):
    """Tests pour la validation de paiement par le commercial"""
    
    def setUp(self):
        self.client = Client()
        
        # Créer commercial
        self.commercial_user = TestDataFactory.create_test_user(
            'commercial@test.com',
            role_code='COMMERCIAL'
        )
        
        # Créer client + réservation + paiement
        self.programme = TestDataFactory.create_programme('Test', 'VENTE')
        self.unite = TestDataFactory.create_unite(self.programme)
        
        self.user = TestDataFactory.create_test_user(
            'client@test.com',
            role_code='CLIENT'
        )
        self.client_profile = TestDataFactory.create_client(self.user)
        self.reservation = TestDataFactory.create_reservation(self.client_profile, self.unite)
        
        self.paiement = Paiement.objects.create(
            reservation=self.reservation,
            montant=500000,
            moyen='virement',
            source='test',
            type_paiement=PaiementType.ACOMPTE,
            statut=PaiementStatus.ENREGISTRE
        )
    
    def test_payment_validation_success(self):
        """Commercial valide un paiement enregistré"""
        self.client.login(email='commercial@test.com', password='test123')
        
        url = reverse('commercial_payment_validate', args=[self.paiement.id])
        response = self.client.post(url)
        
        # Vérifier redirection
        self.assertEqual(response.status_code, 302)
        
        # Vérifier paiement validé
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.statut, PaiementStatus.VALIDE)
    
    def test_payment_validation_404_if_already_validated(self):
        """Tentative de valider 2 fois retourne 404"""
        self.paiement.statut = PaiementStatus.VALIDE
        self.paiement.save()
        
        self.client.login(email='commercial@test.com', password='test123')
        
        url = reverse('commercial_payment_validate', args=[self.paiement.id])
        response = self.client.post(url)
        
        # Doit retourner 404 car paiement n'est plus 'enregistre'
        self.assertEqual(response.status_code, 404)
    
    def test_permission_denied_for_client(self):
        """Client ne peut pas valider les paiements"""
        self.client.login(email='client@test.com', password='test123')
        
        url = reverse('commercial_payment_validate', args=[self.paiement.id])
        response = self.client.post(url)
        
        # Doit rediriger ou retourner 403
        self.assertIn(response.status_code, [302, 403])


# =============================================================================
# TESTS SIGNAUX
# =============================================================================

class SignalEcheanceGenerationTest(TestCase):
    """Tests pour les signaux de génération d'échéances"""
    
    def setUp(self):
        self.programme = TestDataFactory.create_programme('Test', 'LOCATION')
        self.unite = TestDataFactory.create_unite(self.programme)
        self.user = TestDataFactory.create_test_user('client@test.com', role_code='CLIENT')
        self.client_profile = TestDataFactory.create_client(self.user)
        self.reservation = TestDataFactory.create_reservation(self.client_profile, self.unite)
    
    def test_premiere_echeance_after_caution_validated(self):
        """
        GIVEN: Paiement caution créé et validé
        THEN: Première échéance générée automatiquement
        """
        # Vérifier qu'aucune échéance n'existe
        self.assertEqual(self.reservation.echeances_loyer.count(), 0)
        
        # Créer et valider paiement caution
        paiement = Paiement.objects.create(
            reservation=self.reservation,
            montant=2000000,
            moyen='virement',
            source='test',
            type_paiement=PaiementType.CAUTION,
            statut=PaiementStatus.ENREGISTRE
        )
        
        # Valider le paiement
        paiement.statut = PaiementStatus.VALIDE
        paiement.save()
        
        # Vérifier qu'une échéance a été créée
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.echeances_loyer.count(), 1)
        
        echeance = self.reservation.echeances_loyer.first()
        self.assertEqual(echeance.numero_mois, 1)
        self.assertEqual(echeance.statut_paiement, PaiementStatus.ENREGISTRE)
    
    def test_no_duplicate_echeances(self):
        """Signal ne crée pas 2 fois la même échéance"""
        paiement = Paiement.objects.create(
            reservation=self.reservation,
            montant=2000000,
            moyen='virement',
            source='test',
            type_paiement=PaiementType.CAUTION,
            statut=PaiementStatus.ENREGISTRE
        )
        
        # Valider 2 fois
        paiement.statut = PaiementStatus.VALIDE
        paiement.save()
        
        paiement.statut = PaiementStatus.VALIDE
        paiement.save()
        
        # Doit avoir qu'une seule échéance
        self.assertEqual(self.reservation.echeances_loyer.count(), 1)
    
    def test_no_echeance_for_vente(self):
        """Signal ne génère pas d'échéance pour VENTE"""
        programme_vente = TestDataFactory.create_programme('Vente', 'VENTE')
        unite_vente = TestDataFactory.create_unite(programme_vente)
        res_vente = TestDataFactory.create_reservation(self.client_profile, unite_vente)
        
        paiement = Paiement.objects.create(
            reservation=res_vente,
            montant=5000000,
            moyen='virement',
            source='test',
            type_paiement=PaiementType.ACOMPTE,
            statut=PaiementStatus.ENREGISTRE
        )
        
        paiement.statut = PaiementStatus.VALIDE
        paiement.save()
        
        # Aucune échéance
        self.assertEqual(res_vente.echeances_loyer.count(), 0)


# =============================================================================
# TESTS DASHBOARD
# =============================================================================

class CommercialDashboardTest(TestCase):
    """Tests pour le dashboard commercial"""
    
    def setUp(self):
        self.client_http = Client()
        
        self.commercial_user = TestDataFactory.create_test_user(
            'commercial@test.com',
            role_code='COMMERCIAL'
        )
        
        self.programme = TestDataFactory.create_programme('Test', 'LOCATION')
        self.unite = TestDataFactory.create_unite(self.programme)
        
        self.user = TestDataFactory.create_test_user('client@test.com', role_code='CLIENT')
        self.client_profile = TestDataFactory.create_client(self.user)
        self.reservation = TestDataFactory.create_reservation(self.client_profile, self.unite)
    
    def test_dashboard_counts_consistency(self):
        """Compteur pending_payments_count = nombre réel de paiements en attente"""
        # Créer quelques paiements en attente
        for i in range(3):
            Paiement.objects.create(
                reservation=self.reservation,
                montant=500000,
                moyen='virement',
                source=f'test{i}',
                type_paiement=PaiementType.ACOMPTE,
                statut=PaiementStatus.ENREGISTRE
            )
        
        self.client_http.login(email='commercial@test.com', password='test123')
        
        url = reverse('commercial_dashboard')
        response = self.client_http.get(url)
        
        # Vérifier contexte
        self.assertEqual(response.context['pending_payments_count'], 3)


# =============================================================================
# RUNNER TESTS
# =============================================================================

if __name__ == '__main__':
    import unittest
    unittest.main()
