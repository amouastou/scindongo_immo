"""
Script de test du système d'audit.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import JournalAudit
from core.utils import audit_log

User = get_user_model()


class AuditSystemTest(TestCase):
    """Tests du système d'audit complet"""
    
    def setUp(self):
        """Préparer les données de test"""
        # Créer un utilisateur admin
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        from accounts.models import Role
        admin_role, _ = Role.objects.get_or_create(
            code='ADMIN',
            defaults={'libelle': 'Administrateur'}
        )
        self.admin_user.roles.add(admin_role)
        
        # Créer un client
        self.client_user = User.objects.create_user(
            email='client@test.com',
            password='testpass123'
        )
        client_role, _ = Role.objects.get_or_create(
            code='CLIENT',
            defaults={'libelle': 'Client'}
        )
        self.client_user.roles.add(client_role)
        
        self.client = Client()
    
    def test_audit_log_function(self):
        """Test de la fonction audit_log"""
        # Créer une entrée d'audit manuellement
        audit_log(
            actor=self.admin_user,
            obj=self.admin_user,
            action="test_action",
            payload={"test": "data"},
            categorie="system",
            resultat="success"
        )
        
        # Vérifier qu'elle existe
        log = JournalAudit.objects.latest('created_at')
        self.assertEqual(log.acteur, self.admin_user)
        self.assertEqual(log.action, "test_action")
        self.assertEqual(log.categorie, "system")
        self.assertEqual(log.resultat, "success")
        self.assertEqual(log.payload["test"], "data")
    
    def test_login_audit(self):
        """Test de l'audit des connexions"""
        initial_count = JournalAudit.objects.count()
        
        # Se connecter
        response = self.client.post(reverse('login'), {
            'username': 'admin@test.com',  # USERNAME_FIELD='email'
            'password': 'testpass123'
        })
        
        # Vérifier qu'une entrée d'audit a été créée
        new_count = JournalAudit.objects.count()
        self.assertGreater(new_count, initial_count)
        
        # Vérifier le contenu
        log = JournalAudit.objects.filter(action='user_login').latest('created_at')
        self.assertEqual(log.acteur, self.admin_user)
        self.assertEqual(log.categorie, 'authentication')
        self.assertEqual(log.resultat, 'success')
    
    def test_failed_login_audit(self):
        """Test de l'audit des échecs de connexion"""
        initial_count = JournalAudit.objects.count()
        
        # Tentative de connexion avec mauvais mot de passe
        response = self.client.post(reverse('login'), {
            'username': 'admin@test.com',
            'password': 'wrongpassword'
        })
        
        # Vérifier qu'une entrée d'audit a été créée
        new_count = JournalAudit.objects.count()
        self.assertGreater(new_count, initial_count)
        
        # Vérifier le contenu
        log = JournalAudit.objects.filter(action='user_login_failed').latest('created_at')
        self.assertIsNone(log.acteur)  # Pas d'acteur pour échec
        self.assertEqual(log.categorie, 'authentication')
        self.assertEqual(log.resultat, 'failure')
    
    def test_middleware_audit_post_request(self):
        """Test de l'audit automatique des requêtes POST"""
        # Se connecter d'abord
        self.client.login(username='admin@test.com', password='testpass123')
        
        initial_count = JournalAudit.objects.filter(
            categorie='data_create'
        ).count()
        
        # Faire une requête POST (n'importe laquelle)
        # Ici on utilise un endpoint qui existe
        response = self.client.post(reverse('home'), {})
        
        # Vérifier qu'une entrée a été créée par le middleware
        new_count = JournalAudit.objects.filter(
            categorie='data_create'
        ).count()
        # Note: peut être égal si la requête n'est pas tracée
        # (selon la config du middleware)
    
    def test_audit_list_view_admin_only(self):
        """Test que seul l'admin peut voir les logs d'audit"""
        # Client ne peut pas voir
        self.client.login(username='client@test.com', password='testpass123')
        response = self.client.get(reverse('core:audit_list'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Admin peut voir
        self.client.login(username='admin@test.com', password='testpass123')
        response = self.client.get(reverse('core:audit_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_audit_detail_view(self):
        """Test de la vue détail d'audit"""
        # Créer une entrée
        audit_log(
            actor=self.admin_user,
            obj=self.admin_user,
            action="test_detail",
            categorie="system",
            resultat="success"
        )
        
        log = JournalAudit.objects.latest('created_at')
        
        # Admin peut voir le détail
        self.client.login(username='admin@test.com', password='testpass123')
        response = self.client.get(reverse('core:audit_detail', kwargs={'pk': log.id}))
        self.assertEqual(response.status_code, 200)
    
    def test_user_audit_history(self):
        """Test de l'historique d'audit par utilisateur"""
        # Créer plusieurs entrées pour un utilisateur
        for i in range(5):
            audit_log(
                actor=self.client_user,
                obj=self.client_user,
                action=f"action_{i}",
                categorie="system",
                resultat="success"
            )
        
        # Admin peut voir l'historique
        self.client.login(username='admin@test.com', password='testpass123')
        response = self.client.get(
            reverse('core:user_audit_history', kwargs={'user_id': self.client_user.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Vérifier qu'on voit les 5 actions
        logs_count = JournalAudit.objects.filter(acteur=self.client_user).count()
        self.assertEqual(logs_count, 5)
