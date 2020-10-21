import logging

from .loader import load_model_serializer

logger = logging.getLogger(__name__)


class AutoSerializerMixin:
    """Allows for loading serializer classes based on either the action or model type
    """
    model = None

    def get_serializer_class(self):
        """Try to do an autolookup of the model's serializer class
        """
        action_serializer_class = getattr(self, f'{self.action}_serializer_class', None)
        if action_serializer_class:
            return action_serializer_class

        if self.serializer_class:
            return self.serializer_class

        if self.model:
            serializer_class = load_model_serializer(self.model)
            if serializer_class:
                return serializer_class

        logger.warning(
            'Fell through get_serializer_class, did you create %s correctly?',
            self.__class__.__name__
        )
        return super().get_serializer_class()
