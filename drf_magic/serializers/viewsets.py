import logging

from .loader import load_model_serializer

logger = logging.getLogger(__name__)


class AutoSerializerViewMixin:
    """Allows for loading serializer classes based on either the action or model type
    """
    model = None

    def get_serializer_class(self):
        """Try to do an autolookup of the model's serializer class
        """
        if hasattr(self, 'action') and hasattr(self, f'{self.action}_serializer_class'):
            return getattr(self, f'{self.action}_serializer_class', None)

        if self.serializer_class:
            return self.serializer_class

        if self.model:
            serializer_class = load_model_serializer(self.model)
            if serializer_class:
                return serializer_class

        if hasattr(self, 'get_queryset'):
            try:
                qs = self.get_queryset(default_queryset=True)
            except TypeError:
                qs = self.get_queryset()
            if qs and qs.model:
                serializer_class = load_model_serializer(qs.model)
                if serializer_class:
                    return serializer_class

        logger.warning(
            'Fell through get_serializer_class, did you create %s correctly?',
            self.__class__.__name__
        )
        return super().get_serializer_class()
