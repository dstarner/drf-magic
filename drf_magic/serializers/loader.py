import importlib
import inspect
import logging

from django.apps import AppConfig
from django.db.models import Model
from rest_framework.serializers import ModelSerializer

__all__ = [
    'register_main_serializer',
    'load_model_serializer',
]


logger = logging.getLogger(__name__)


# Used to easily get a serializer for a model type
__serializer_mapper = {
    # <model class> : <serializer class>
}


def register_main_serializer(serializer_class):
    """
    Registers a ModelSerializer as the main serializer for a model type when attached
    as a decorator on the serializer class declaration. It uses the Meta.model attribute,
    and each model can only have a single main serializer associated with it.
    """
    meta_class = getattr(serializer_class, '_meta', serializer_class.Meta)
    model_class = meta_class.model

    if model_class in __serializer_mapper and __serializer_mapper[model_class] != serializer_class:
        logger.error('Two serializers listed %s as their model, be careful', model_class)

    if not (inspect.isclass(model_class) and issubclass(model_class, Model)):
        raise TypeError('model_class should be a Django model class')

    if not (inspect.isclass(model_class) and issubclass(serializer_class, ModelSerializer)):
        raise TypeError(
            'register_main_serializer should only be placed on a'
            'class definition that subclass ModelSerializer'
        )

    __serializer_mapper[model_class] = serializer_class
    return serializer_class


def load_model_serializer(model_class):
    """Used to safely load a serializer from the main serializer-to-model map
    """
    return __serializer_mapper.get(model_class, None)


class AutoSerializerAppConfig(AppConfig):
    """Will attempt to load and register the app's serializers automatically on app load
    """

    serializer_path = 'serializers'

    def initialize_serializers(self):
        if self.serializer_path:
            if isinstance(self.serializer_path, (str)):
                self.serializer_path = [self.serializer_path]
            for path in self.serializer_path:
                import_path = '.'.join([self.name, path])
                importlib.import_module(import_path)


class MissingSerializerException(Exception):
    pass
