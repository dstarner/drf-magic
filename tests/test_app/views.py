from rest_framework.viewsets import ModelViewSet

from drf_magic.views.mixins import (
    AutoNestedRouterViewsetMixin, AutoSerializerViewMixin
)

from .models import Child, GrandParent, Parent

__all__ = [
    'GrandParentViewSet',
    'ParentViewSet',
    'ChildViewSet',
]


class GrandParentViewSet(AutoNestedRouterViewsetMixin, AutoSerializerViewMixin, ModelViewSet):
    model = GrandParent


class ParentViewSet(AutoNestedRouterViewsetMixin, AutoSerializerViewMixin, ModelViewSet):
    model = Parent


class ChildViewSet(AutoNestedRouterViewsetMixin, AutoSerializerViewMixin, ModelViewSet):
    model = Child
