from django.apps import AppConfig


class EmrConfig(AppConfig):
    name = 'apps.emr'
    label = 'emr'
    verbose_name = 'Electronic Medical Records'

    def ready(self) -> None:
        import apps.emr.signals  # noqa: F401
