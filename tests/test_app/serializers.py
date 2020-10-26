from rest_framework import serializers

from drf_magic.serializers import WritableNestedSerializer
from drf_magic.serializers.loader import register_main_serializer

from .models import Child, GrandParent, Parent, Person


@register_main_serializer
class PersonSerializer(serializers.ModelSerializer):
    """Main serializer class for converting Person instances to JSON and back
    """

    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'occupation']


@register_main_serializer
class GrandParentSerializer(serializers.ModelSerializer):

    class Meta:
        model = GrandParent
        fields = ['gp_value', 'id']


class GrandParentNestedSerializer(WritableNestedSerializer):

    class Meta:
        model = GrandParent
        fields = ['gp_value', 'id']


@register_main_serializer
class ParentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parent
        fields = ['p_value', 'id', 'grand_parent']


class ParentNestedSerializer(WritableNestedSerializer):

    class Meta:
        model = Parent
        fields = ['p_value', 'id']


@register_main_serializer
class ChildSerializer(serializers.ModelSerializer):

    class Meta:
        model = Child
        fields = ['c_value', 'id', 'parent']
