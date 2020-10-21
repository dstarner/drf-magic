from .access.apps import AutoAccessorAppConfig
from .serializers.loader import AutoSerializerAppConfig


class MagicAppConfig(AutoAccessorAppConfig, AutoSerializerAppConfig):
    """Performs serializer and accessor configuration as well
    """

    def ready(self):
        self.initialize_accessors()
        self.initialize_serializers()
        return super().ready()


class DRFMagicConfig(MagicAppConfig):
    name = 'drf_magic'
    verbose_name = 'Django REST Framework Magic'

    def ready(self):
        from .access import patch, signals  # noqa
        return super().ready()
