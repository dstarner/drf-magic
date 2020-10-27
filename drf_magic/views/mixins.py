import inspect
import logging

import inflection
from django.core.exceptions import ObjectDoesNotExist
from drf_yasg2 import openapi
from drf_yasg2.utils import swagger_auto_schema
from rest_framework.decorators import action as drf_action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import BooleanField, Serializer

from ..access.accessors import (
    access_registry, check_user_access, instance_to_accessor
)
from ..routers import NestedRouter
from ..serializers.viewsets import AutoSerializerViewMixin
from ..utils import classproperty

__all__ = [
    'AutoNestedRouterViewsetMixin',
    'AutoSerializerViewMixin',
    'AutoNestedAccessorPermissionMixin',
    'SlugLookupMixin',
]

logger = logging.getLogger(__name__)


class SlugLookupMixin:
    """The default lookup for any viewset that inherits this will be via its 'slug' field
    """
    lookup_url_kwarg = 'slug'
    lookup_field = 'slug'


class AutoNestedRouterViewsetMixin(metaclass=classproperty.meta):
    """Allows for automatic router management and viewset nesting abilities
    """

    model = None  # used for generating router and url configurations

    # If the model's parent field is not named the same as the lookup kwarg, include
    # this on the subclass and it will perform the foreign key lookup against it
    parent_related_field = None

    # Explicitly set the URL routing and base_name
    _lookup_field = 'id'
    _lookup_url_kwarg = 'id'

    # Pointer to the parent router, building a linked list implementation
    router = None

    @classmethod
    def alter_parent_filters(cls, filters):
        """
        Allows for setting extra queryset parameters without needing to override get_queryset.
        Return a list of filters that should be provided to reduce the queryset
        """
        return filters

    def get_queryset(self, default_queryset=False):
        """
        Tries to build the correct queryset from the current view and parent
        routes.
        """
        qs = None
        if getattr(self, 'queryset', None) is not None:
            qs = self.queryset._clone()
        elif getattr(self, 'model', None):
            qs = self.model.objects.all()
        else:
            qs = super().get_queryset()

        if default_queryset:
            return qs

        # If being accessed through the schema builder, return none
        try:
            format_requested = self.request.GET.get('format', 'json')
        except AttributeError:
            format_requested = 'unknown'
        if any([
                format_requested in ['openapi', ['openapi']],
                self.parent_view() is not None and self.kwargs == {}
        ]):
            return qs.none()

        # If we are a subroute, handle looking up the parent filters as well
        parent_filters = self.build_parent_filter_context(kwargs=self.kwargs)
        viewset_filters = self.alter_parent_filters(parent_filters if isinstance(parent_filters, dict) else dict())
        if viewset_filters and isinstance(viewset_filters, dict):
            parent_filters = viewset_filters

        # Add the parent filters to the current QS to return a scoped queryset
        if parent_filters:
            logger.debug(
                'Adding the following parent filters to the %s queryset: %s',
                self.model.__name__, parent_filters
            )
            qs = qs.filter(**parent_filters)
        return qs

    @classmethod
    def build_parent_filter_context(cls, kwargs=None, context=None):
        """
        Iterates through the parent viewsets and builds together the queryset filters to
        automatically return only the resources under that path
        """
        if not context:
            context = {}
        if not kwargs:
            kwargs = {}
        parents = [cls]
        parent_viewset = cls.parent_view()

        # Generates a long string of the deepest nested queryset filter() key needed
        # For example "tier__stack__cluster". This is used in the next step
        filter_prefix = []
        while parent_viewset:
            lookup_prefix = parent_viewset.lookup_url_prefix
            child_viewset = parents[0]
            # Allows the child to override the parent's prefix in case it doesn't exactly line up
            if hasattr(child_viewset, 'parent_related_field') and isinstance(child_viewset.parent_related_field, str):
                logger.debug(
                    'Overriding lookup_prefix from "%s" to "%s"', lookup_prefix, child_viewset.parent_related_field
                )
                lookup_prefix = child_viewset.parent_related_field
            filter_prefix.append(lookup_prefix)

            parents = [parent_viewset] + parents
            parent_viewset = parent_viewset.parent_view()

        # Builds the longest parent filter, so that we can
        # break it down into smaller parts in the next step
        filter_prefix = '__'.join(filter_prefix)

        # Iterate through the field__filter__list and add each based on the request kwargs
        for i, parent in enumerate(parents):
            lookup_prefix = parent.lookup_url_prefix

            lookup_url_kwarg = parent.prefixed_lookup_url_kwarg
            lookup_field = parent.lookup_field
            if filter_prefix:
                lookup_field = f'{filter_prefix}__{lookup_field}'

            if lookup_url_kwarg in kwargs:
                context[lookup_field] = kwargs[lookup_url_kwarg]
            elif i != len(parents) - 1:
                raise AssertionError(f'Could not find {lookup_url_kwarg} in request kwargs {kwargs}')

            # Chop off the last filter field prefix for the next iteration
            filter_prefix = filter_prefix.rsplit('__', 2)[0]

        return cls.alter_parent_filters(context)

    # ROUTER METHODS
    # --------------

    @classmethod
    def _build_wrapped_router(cls, router):
        router_name = inflection.camelize(router.name.replace(' ', '_'), True)
        attrs = dict(vars(cls))
        WrapperClass = type(f'{cls.__name__}_{router_name}_Wrapper', (cls,), attrs)
        WrapperClass.router = router
        router.register(
            cls.url_route, WrapperClass,
            base_name=cls.base_name
        )
        return WrapperClass

    @classmethod
    def add_to_router(cls, router):
        """Adds the class to the given router instance

        It does this by creating a dynamic wrapper class and passing that wrapper class
        to the router. This is because the router.register function MUST take a class as
        its argument. This would be fine, but in the case where a viewset class can be used
        multiple times, it breaks because a class can only have one 'router' pointer. Having
        wrapper classes means that a ViewSet class can be used as many times as desired.
        """
        return cls._build_wrapped_router(router)

    @classmethod
    def add_as_nested_router(cls, parent_router):
        """Adds the viewset to the parent_router and then returns a router instance to use under the viewset
        """
        wrapper_class = cls._build_wrapped_router(parent_router)
        return NestedRouter(
            parent_router,
            wrapper_class.url_route,
            lookup=wrapper_class.lookup_url_prefix,
            name=wrapper_class.router_name,
            root_viewset_cls=wrapper_class,
        )

    @classmethod
    def parent_view(cls):
        """Returns the parent view[set] class if one is configured
        """
        if not cls.router:
            return None
        return cls.router.root_viewset_cls if hasattr(cls.router, 'root_viewset_cls') else None

    @classmethod
    def parent_view_for_model(cls, model):
        """Returns the first parent viewset associated with the given model
        """
        parent_viewset = cls.parent_view()
        while parent_viewset:
            if hasattr(parent_viewset, 'model') and parent_viewset.model == model:
                return parent_viewset
            elif hasattr(parent_viewset, 'get_queryset'):
                qs = parent_viewset().get_queryset(default_queryset=True)
                if qs.model == model:
                    return parent_viewset

            parent_viewset = parent_viewset.parent_view() if hasattr(parent_viewset, 'parent_view') else None
        return None

    def get_object(self, permission_check=True):
        """
        Returns the object the view is displaying.

        Overridden so that we can skip the permission check if desired
        I did not change anything meaningful other than permission_check
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        if permission_check:
            self.check_object_permissions(self.request, obj)
        return obj

    # ------------------------------------------------------------------------------------
    # The following @classproperty values represent the defaults configured in this mixin.
    # If a custom value is desired, it can be overridden on the concrete view[set] class

    @classproperty
    def base_name(self):  # pragma: no cover
        if not self.model:
            raise ValueError(f'expected {self} ".model" or ".base_name" to be defined')
        if self.router:
            return self.router.get_default_basename(self)
        default = inflection.dasherize(self.model._meta.verbose_name.lower().replace(' ', '_'))
        return default

    @classproperty
    def url_route(self):  # pragma: no cover
        """Returns the URL portion for this view
        """
        if not self.model:
            raise ValueError(f'expected {self} ".model" or ".url_route" to be defined')
        return inflection.dasherize(self.model._meta.verbose_name_plural.lower().replace(' ', '_'))

    @classproperty
    def lookup_field(self):  # pragma: no cover
        """Returns the lookup field that is used on the model for get_object()
        """
        if SlugLookupMixin in self.mro():
            return SlugLookupMixin.lookup_field
        return self._lookup_field

    @classproperty
    def lookup_url_kwarg(self):  # pragma: no cover
        """Returns the URL regex parameter name that is used on the model for get_object()
        """
        if SlugLookupMixin in self.mro():
            return SlugLookupMixin.lookup_url_kwarg
        return self._lookup_url_kwarg

    @classproperty
    def lookup_url_prefix(self):  # pragma: no cover
        """When a child viewset is added, this prefix is appended to its lookup url kwarg
        """
        if not self.model:
            raise ValueError(f'expected {self} ".model" or ".lookup_url_prefix" to be defined')
        default = inflection.underscore(self.model._meta.verbose_name.lower().replace(' ', '_'))
        return default

    @classproperty
    def prefixed_lookup_url_kwarg(self):  # pragma: no cover
        """
        If accessing the URL kwarg on a parent, its lookup_url_kwarg will be prefixed,
        so this is a helper method that can adjust the URL kwargs key lookup dynamically
        """
        return f'{self.lookup_url_prefix}_{self.lookup_url_kwarg}'

    @classproperty
    def router_name(self):  # pragma: no cover
        """Returns the router name by looking up against the configured model
        """
        if not self.model:
            raise ValueError(f'expected {self} ".model" or ".router_name" to be defined')
        return inflection.humanize(self.model._meta.verbose_name.lower().replace(' ', '_'))


class AutoNestedAccessorPermissionMixin(AutoNestedRouterViewsetMixin):

    # By default, check if a request has access to the parent view[set]
    check_parent_permissions = True

    # Allows settings a base role that is required for all actions (like must have read role)
    base_role = None

    @classmethod
    def check_view_permission(cls, request, url_kwargs, action='read'):
        """
        Checks if the request has permission to perform action on the view
        Note that this works recursively, calling up the parent viewsets as well
        unless check_parent_permissions is set, which can be used in testing
        """
        parent = cls.parent_view()
        if parent and getattr(cls, 'check_parent_permissions', True):
            # This little block of code is responsible for "bumping up" the URL kwargs
            # as if the request was on the parent viewset instead of the child.
            # It removes the current-level kwarg and removes the prefix from the
            # immediate parent so that it becomes the current level.
            nested_url_kwargs = url_kwargs.copy()
            nested_url_kwargs.pop(cls.lookup_url_kwarg, None)
            if parent.prefixed_lookup_url_kwarg in nested_url_kwargs:
                nested_url_kwargs[parent.lookup_url_kwarg] = url_kwargs[parent.prefixed_lookup_url_kwarg]
                nested_url_kwargs.pop(parent.prefixed_lookup_url_kwarg, None)

            # Recursively call on the parent (done before children calls)
            # Note that for parents, we just need read permission to access a child view
            if not parent.check_view_permission(request, nested_url_kwargs, action='read'):
                logger.debug('PERMISSIONS: %s denied permission to child %s', parent.__name__, cls.__name__)
                return False

        if not cls.model:
            return True

        view = cls(request=request, kwargs=url_kwargs)
        instance = None
        if cls.lookup_url_kwarg in url_kwargs:
            instance = view.get_object(permission_check=False)
        return check_user_access(
            request.user, cls.model, action,
            instance=instance, request=request, view=cls, url_kwargs=url_kwargs
        )

    def get_queryset(self):
        """
        Looks at self.model and returns a subset of items using the accessor class
        if the base_role is set on the viewset
        """
        qs = super().get_queryset()
        if self.model and self.model in access_registry:
            if getattr(self, 'swagger_fake_view', False):
                return self.model.objects.none()
            access_class = access_registry[self.model]
            accessor = access_class(self.request.user, self.request, self)
            qs = accessor.scope_queryset(queryset=qs, filtered_role=self.base_role)

        return qs


class CapabilitiesViewsetMixin:
    """Mixin that allows a ViewSet to take advantage of the RBAC system
    """

    model = None

    @classmethod
    def add_to_router(cls, router):
        """Will return a nested router if the view model has role fields on it
        """
        if cls.model and hasattr(cls.model, '__implicit_role_fields'):
            return cls.add_as_nested_router(router)
        return super().add_to_router(router)

    @classmethod
    def add_as_nested_router(cls, parent_router):
        """Adds the viewset to the parent_router and then returns a router instance to use under the viewset
        """
        router = super().add_as_nested_router(parent_router)
        # TODO: add the role viewset
        # if cls.model and hasattr(cls.model, '__implicit_role_fields'):
        #     RoleViewset.add_to_router(router)
        return router

    @swagger_auto_schema(method='get', manual_parameters=[
        openapi.Parameter(
            name='action', in_=openapi.IN_QUERY,
            type=openapi.TYPE_ARRAY,
            description='Filter to check only certain action(s) on the model\'s accessor.',
            items=openapi.Items(type=openapi.TYPE_STRING),
            collection_format='multi'
        )
    ])
    @drf_action(detail=True, methods=['GET'], url_path='capabilities')
    def capabilities(self, request, **kwargs):
        """
        ===
        title: Get Capable Actions for the {verbose_name} Resource
        ---
        Returns a list of actions and whether or not the current user has permission to perform
        those actions against the given resource.
        """
        lookup_kwarg = self.lookup_url_kwarg
        kwarg_value = kwargs.get(lookup_kwarg, None)
        if not kwarg_value:
            raise APIException(
                f'Could not find URL lookup \'{lookup_kwarg}\' in the URL parameters. Please '
                'note the attempted URL and contact the Babka team to fix this server issue.'
            )
        try:
            instance = self.get_object(permission_check=False)
        except ObjectDoesNotExist:
            raise NotFound(
                f'A matching {self.model._meta.verbose_name} could not be found. If this is '
                'a recurring issue, please contact the Babka team.'
            )

        method_list = request.GET.getlist('action', [])
        if not method_list:
            # If the request does not specify what actions to check, then we try to inspect the
            # instance's model accessor to get _all possible_ actions to test each of them
            accessor = access_registry[self.model](request.user, instance=instance)
            raw_methods = inspect.getmembers(accessor, predicate=inspect.ismethod)
            method_list = [x.replace('can_', '') for x, _ in raw_methods if x.startswith('can_')]
        logger.debug('capabilities for "%s" for actions "%s" against "%s"', request.user, method_list, instance)
        accessor = instance_to_accessor(instance)(request.user, request=request, instance=instance, view=self)
        capabilities = accessor.get_user_capabilities(method_list=method_list)
        return Response({'username': request.user.username, 'capabilities': capabilities})

    def __getattr__(self, name):
        """
        Allows for the dynamic creation of a serializer class that returns the capabilities of a
        user for that specific object
        """
        if name == 'capabilities_serializer_class':
            accessor = access_registry.get(self.model, None)
            if not accessor:
                return None
            if self.model in _capabilities_serializer_classes:
                return _capabilities_serializer_classes[self.model]

            raw_methods = inspect.getmembers(accessor(self.request.user, view=self), predicate=inspect.ismethod)
            method_list = [x.replace('can_', '') for x, _ in raw_methods if x.startswith('can_')]
            attrs = {
                method: BooleanField(
                    read_only=True,
                    help_text=(
                        f'Describes whether or not the user can perform "{method}" actions '
                        f'against the given {self.model.__name__} instance.'
                    )
                ) for method in method_list
            }
            serializer_class = type(f'{self.model.__name__}CapabilitiesSerializer', (Serializer,), attrs)
            _capabilities_serializer_classes[self.model] = serializer_class

            return serializer_class
        return self.__getattribute__(name)


_capabilities_serializer_classes = dict()
