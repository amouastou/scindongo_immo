from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'

    def ready(self):
        """Import signaux lors du démarrage de l'app."""
        import catalog.signals  # noqa

