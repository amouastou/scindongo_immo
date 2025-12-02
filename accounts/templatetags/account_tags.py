from django import template

register = template.Library()


@register.filter(name="has_role")
def has_role(user, code: str) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not hasattr(user, "roles"):
        return False
    return user.roles.filter(code__iexact=code).exists()
