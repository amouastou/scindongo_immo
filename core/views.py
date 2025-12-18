"""
Vues pour la consultation du journal d'audit.
"""

from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from accounts.mixins import RoleRequiredMixin
from core.models import JournalAudit


class AuditListView(RoleRequiredMixin, ListView):
    """
    Liste des entrées d'audit (ADMIN uniquement).
    Avec filtres par utilisateur, catégorie, action, date.
    """
    model = JournalAudit
    template_name = 'core/audit_list.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    required_roles = ["ADMIN"]
    
    def get_queryset(self):
        """Filtrer les logs selon les paramètres GET"""
        qs = JournalAudit.objects.select_related('acteur').all()
        
        # Filtre par utilisateur
        user_id = self.request.GET.get('user')
        if user_id:
            qs = qs.filter(acteur_id=user_id)
        
        # Filtre par catégorie
        categorie = self.request.GET.get('categorie')
        if categorie:
            qs = qs.filter(categorie=categorie)
        
        # Filtre par action
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action__icontains=action)
        
        # Filtre par résultat
        resultat = self.request.GET.get('resultat')
        if resultat:
            qs = qs.filter(resultat=resultat)
        
        # Filtre par période
        periode = self.request.GET.get('periode')
        if periode:
            now = timezone.now()
            if periode == '1h':
                qs = qs.filter(created_at__gte=now - timedelta(hours=1))
            elif periode == '24h':
                qs = qs.filter(created_at__gte=now - timedelta(days=1))
            elif periode == '7d':
                qs = qs.filter(created_at__gte=now - timedelta(days=7))
            elif periode == '30d':
                qs = qs.filter(created_at__gte=now - timedelta(days=30))
        
        # Filtre par date personnalisée
        date_debut = self.request.GET.get('date_debut')
        date_fin = self.request.GET.get('date_fin')
        if date_debut:
            qs = qs.filter(created_at__gte=date_debut)
        if date_fin:
            qs = qs.filter(created_at__lte=date_fin)
        
        # Recherche textuelle
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(action__icontains=search) |
                Q(objet_type__icontains=search) |
                Q(acteur__email__icontains=search)
            )
        
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques générales
        context['total_logs'] = JournalAudit.objects.count()
        context['logs_24h'] = JournalAudit.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # Stats par catégorie (24h)
        context['stats_categories'] = JournalAudit.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).values('categorie').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Stats par résultat (24h)
        context['stats_resultats'] = JournalAudit.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).values('resultat').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Échecs récents (pour alertes)
        context['recent_failures'] = JournalAudit.objects.filter(
            resultat='failure',
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).order_by('-created_at')[:10]
        
        # Catégories disponibles pour le filtre
        context['categories'] = [
            ('authentication', 'Authentification'),
            ('authorization', 'Autorisation'),
            ('data_create', 'Création'),
            ('data_read', 'Lecture'),
            ('data_update', 'Mise à jour'),
            ('data_delete', 'Suppression'),
            ('business_logic', 'Logique métier'),
            ('file_upload', 'Upload'),
            ('file_download', 'Téléchargement'),
            ('payment', 'Paiement'),
            ('contract', 'Contrat'),
            ('reservation', 'Réservation'),
            ('financing', 'Financement'),
            ('document', 'Document'),
            ('user_management', 'Gestion utilisateur'),
            ('system', 'Système'),
        ]
        
        # Résultats disponibles pour le filtre
        context['resultats'] = [
            ('success', 'Succès'),
            ('failure', 'Échec'),
            ('partial', 'Partiel'),
            ('pending', 'En attente'),
        ]
        
        return context


class AuditDetailView(RoleRequiredMixin, DetailView):
    """
    Détail d'une entrée d'audit (ADMIN uniquement).
    """
    model = JournalAudit
    template_name = 'core/audit_detail.html'
    context_object_name = 'audit_log'
    required_roles = ["ADMIN"]


class UserAuditHistoryView(RoleRequiredMixin, ListView):
    """
    Historique d'audit pour un utilisateur spécifique (ADMIN uniquement).
    """
    model = JournalAudit
    template_name = 'core/user_audit_history.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    required_roles = ["ADMIN"]
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return JournalAudit.objects.filter(
            acteur_id=user_id
        ).select_related('acteur').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        
        # Récupérer l'utilisateur
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            context['target_user'] = User.objects.get(id=user_id)
        except User.DoesNotExist:
            context['target_user'] = None
        
        # Stats pour cet utilisateur
        context['total_actions'] = JournalAudit.objects.filter(acteur_id=user_id).count()
        context['actions_24h'] = JournalAudit.objects.filter(
            acteur_id=user_id,
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # Actions par catégorie
        context['stats_categories'] = JournalAudit.objects.filter(
            acteur_id=user_id
        ).values('categorie').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return context
