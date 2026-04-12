from django.apps import AppConfig


class BillingConfig(AppConfig):
    name = 'apps.billing'
    label = 'billing'
    verbose_name = 'Billing & POS'

    def ready(self) -> None:
        import apps.billing.signals  # noqa: F401
