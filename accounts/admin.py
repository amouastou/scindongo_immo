from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Role, PasswordResetToken


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "created_at", "updated_at")
    search_fields = ("code", "libelle")
    ordering = ("code",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informations personnelles"), {"fields": ("first_name", "last_name", "telephone")}),
        (
            _("Rôles et permissions"),
            {"fields": ("roles", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("Dates importantes"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "first_name",
                "last_name",
                "telephone",
                "password1",
                "password2",
                "roles",
                "is_staff",
                "is_active",
            ),
        }),
    )

    list_display = ("email", "first_name", "last_name", "telephone", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "telephone")
    ordering = ("email",)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "is_used", "expires_at", "ip_address", "created_at")
    list_filter = ("is_used", "created_at", "expires_at")
    search_fields = ("user__email", "token", "ip_address")
    readonly_fields = ("token", "created_at", "updated_at", "user", "expires_at", "ip_address")
    ordering = ("-created_at",)
    
    def has_add_permission(self, request):
        # Empêcher la création manuelle de tokens dans l'admin
        return False
    
    def has_change_permission(self, request, obj=None):
        # Empêcher la modification de tokens dans l'admin (sécurité)
        return False
