from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Role


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
