# core/templatetags/form_tags.py
from django import template

register = template.Library()


@register.filter
def add_class(field, css):
    """
    Usage dans les templates :
        {{ form.champ|add_class:"form-control" }}
    """
    return field.as_widget(attrs={"class": css})
