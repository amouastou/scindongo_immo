from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin générique pour restreindre l'accès à certains rôles métiers."""

    required_roles: list[str] = []

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not self.required_roles:
            return True
        return user.roles.filter(code__in=[c.upper() for c in self.required_roles]).exists()
