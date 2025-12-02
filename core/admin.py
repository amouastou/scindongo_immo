from django.contrib import admin
from .models import Document, JournalAudit


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('titre', 'objet_type', 'created_at')
    search_fields = ('titre', 'objet_type')


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ('objet_type', 'action', 'acteur', 'created_at')
    search_fields = ('objet_type', 'action', 'acteur__email')
    list_filter = ('action',)
