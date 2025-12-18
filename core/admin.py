from django.contrib import admin
from .models import Document, JournalAudit


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('titre', 'objet_type', 'created_at')
    search_fields = ('titre', 'objet_type')


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'acteur', 'categorie', 'action', 
        'objet_type', 'resultat', 'ip_address'
    )
    list_filter = (
        'categorie', 'resultat', 'created_at', 'methode_http'
    )
    search_fields = (
        'acteur__email', 'action', 'objet_type', 
        'ip_address', 'url_path'
    )
    readonly_fields = (
        'created_at', 'acteur', 'objet_type', 'objet_id', 
        'action', 'categorie', 'resultat', 'payload', 
        'ip_address', 'user_agent', 'session_key', 
        'methode_http', 'url_path'
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        """Interdire l'ajout manuel d'entrées d'audit"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Interdire la modification des entrées d'audit"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permettre la suppression uniquement aux superusers"""
        return request.user.is_superuser
