import importlib
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AutoAccessorAppConfig(AppConfig):
    """Will attempt to load and register the app's accessors automatically
    """

    accessor_path = 'accessors'

    def initialize_accessors(self):
        if self.accessor_path:
            if isinstance(self.accessor_path, (str)):
                self.accessor_path = [self.accessor_path]
            for path in self.accessor_path:
                import_path = '.'.join([self.name, path])
                try:
                    importlib.import_module(import_path)
                except ImportError:
                    logger.error('Could not import "%s"\'s accessors at %s', self.name, import_path)
