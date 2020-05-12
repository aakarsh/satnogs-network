"""SatNOGS Network Base app config"""
from django.apps import AppConfig


class BaseConfig(AppConfig):
    """Set configuration of the SatNOGS Network Base app"""
    name = 'network.base'
    verbose_name = "Base"

    def ready(self):
        from network.base import signals  # noqa: F401; pylint: disable=C0415,W0611
