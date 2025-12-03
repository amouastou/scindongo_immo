from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Enregistrer les signals lors du démarrage de l'app."""
        import core.signals  # noqa
