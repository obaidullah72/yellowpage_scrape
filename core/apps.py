from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        if settings.RUN_SCHEDULER:
            from .tasks import start_scheduler

            start_scheduler()
