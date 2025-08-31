from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'

    def ready(self):  # type: ignore[override]
        # Hook up signals (auto-create Profile for new Users)
        from . import signals  # noqa: F401
