"""
URLs pour le module core (audit, documents).
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Audit
    path('audit/', views.AuditListView.as_view(), name='audit_list'),
    path('audit/<uuid:pk>/', views.AuditDetailView.as_view(), name='audit_detail'),
    path('audit/user/<uuid:user_id>/', views.UserAuditHistoryView.as_view(), name='user_audit_history'),
]
