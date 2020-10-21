from django.core.exceptions import (
    FieldError, MultipleObjectsReturned, ObjectDoesNotExist
)
from rest_framework.serializers import (
    ModelSerializer, Serializer, ValidationError
)

from ..utils import dict_to_filter_params


class ReadOnlySerializer(Serializer):
    """Serializer used for ReadOnly operations
    """

    def create(self, validated_data):
        raise AssertionError('Cannot call create against ReadOnlySerializer')

    def update(self, instance, validated_data):
        return self.create(validated_data)


class WritableNestedSerializer(ModelSerializer):
    """Returns a nested representation of an object on read, but accepts only a primary key on write.
    """

    def get_fields(self):
        assert hasattr(self.Meta, 'field_lookup'), (
            'Class {serializer_class} missing "Meta.field_lookup" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )

        return super().get_fields()

    def to_internal_value(self, data):

        if data is None:
            return None

        # Dictionary of related object attributes
        if isinstance(data, dict):
            params = dict_to_filter_params(data)
            try:
                return self.Meta.model.objects.get(**params)
            except ObjectDoesNotExist:
                raise ValidationError(
                    'Related object not found using the provided attributes: {}'.format(params)
                )
            except MultipleObjectsReturned:
                raise ValidationError(
                    'Multiple objects match the provided attributes: {}'.format(params)
                )
            except FieldError as e:
                raise ValidationError(e)

        correct_type_data = getattr(self.Meta, 'cast_func', lambda x: x)(data)
        try:
            return self.Meta.model.objects.get(**{self.Meta.field_lookup: correct_type_data})
        except ObjectDoesNotExist:
            raise ValidationError(
                f'Related object not found using the provided lookup: {self.Meta.field_lookup}={correct_type_data}'
            )


def get_nested_serializer(instance, key):
    """Returns the instance's nested serializer under the 'key' field with its data filled out
    """
    serializer_class = instance._declared_fields.get(key).__class__
    serializer = serializer_class(data=instance.validated_data[key])
    serializer.is_valid(raise_exception=True)
    return serializer
