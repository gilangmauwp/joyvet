from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'
    label = 'core'
    verbose_name = 'Core'

    def ready(self) -> None:
        import apps.core.signals  # noqa: F401
