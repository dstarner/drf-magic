import inspect
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from rest_framework.exceptions import ParseError, PermissionDenied

from ..settings import magic_settings

logger = logging.getLogger(__name__)


# Used to easily lookup a mapping between model classes and the accessors that control them
access_registry = {
    # <model_class>: <access_class>,
    # ...
}
missing_warned_about = set()


def instance_to_accessor(obj):
    """Given a model instance, this returns the model accessor for it
    """
    return access_registry.get(obj._meta.concrete_model, None)


def check_user_access(user, model_class, action, request=None, view=None, instance=None, url_kwargs=None):
    """
    Return True if user can perform action against model_class with the
    provided parameters.
    """
    if not inspect.isclass(model_class):
        instance = model_class
        model_class = model_class._meta.concrete_model
    access_class = access_registry.get(model_class, None)
    if not access_class:
        if model_class not in missing_warned_about:
            logger.warning(
                '%s model class is not present in the access registry, defaulting to %s value',
                model_class, 'magic_settings.ALLOW_ON_MISSING_ACCESSOR'
            )
        missing_warned_about.add(model_class)
        return magic_settings.ALLOW_ON_MISSING_ACCESSOR
    access_instance = access_class(user, request=request, view=view, instance=instance, url_kwargs=url_kwargs)
    access_method = getattr(access_instance, 'can_%s' % action, None)
    if action == 'capabilities':
        return True
    if not access_method:
        logger.debug(
            'Action "%s" for "%s" does not have an accessor method, allowing full access.',
            action, model_class.__name__
        )
        return True
    result = access_method()
    logger.debug('check_user_access %s.%s instance=%r returned %r', access_instance.__class__.__name__,
                 getattr(access_method, '__name__', 'unknown'), instance, result)
    return result


class BaseAccess:
    """
    Base class for checking user access to a given model.  Subclasses should
    define the model attribute, override the get_queryset method to return only
    the instances the user should be able to view, and override/define can_*
    methods to verify a user's permission to perform a particular action.
    """
    model = None

    def __init__(self, user, request=None, view=None, instance=None, url_kwargs=None):
        """Request will be provided on all real-world lookups

        Note that self.kwargs will be set to request.parser_context['kwargs]
        UNLESS they are explicitly given in the constructor
        """
        self.user = user
        self.request = request
        self.view = view
        self._instance = instance  # retrieved through a property
        self.kwargs = None
        if url_kwargs:
            self.kwargs = url_kwargs
        elif self.request and hasattr(self.request, 'parser_context'):
            self.kwargs = self.request.parser_context['kwargs']

        if self.model:
            if self.model in access_registry and not isinstance(self, access_registry[self.model]):
                raise ValueError(
                    f'Model accessor for {self.model} already defined as {access_registry[self.model].__name__}'
                )
            access_registry[self.model] = self.__class__

    @property
    def instance(self):
        """Retrieves the instance associated with the accessor
        """
        if self._instance:
            return self._instance

        if not self.view:
            raise ValueError(
                'Getting instance from accessor requires either instance=<value> in constructor'
                ' or a view=<value> to be passed in the constructor.'
            )
        if getattr(self.view, 'swagger_fake_view', False):
            return None
        return self.view.get_object()

    def subaccessor(self, model_class_or_instance, instance=None):
        """Allows creation of an accessor for the given model class with the same user / request
        """
        model_class = model_class_or_instance
        if not inspect.isclass(model_class):
            model_class = type(model_class)
            if not instance:
                instance = model_class_or_instance
        return access_registry[model_class](self.user, request=self.request, view=self.view, instance=instance)

    def scope_queryset(self, queryset, filtered_role=None):
        """
        Return the default queryset for the user against the model and optionally filter
        results by a role that the user must be a member of
        """
        if filtered_role and hasattr(self.model, 'scope_accessible_queryset'):
            queryset = self.model.scope_accessible_queryset(queryset, self.user, filtered_role)
        return queryset

    # DIFFERENT PERMISSION METHODS
    # ----------------------------

    def _default_response(self, action, auto_response=True):  # pragma: no cover
        logger.debug(
            'Using the default permission response of "%r" for %s\'s can_%s accessor method',
            auto_response, type(self), action
        )
        return auto_response

    def can_read(self):  # pragma: no cover
        """By default, everyone can read
        """
        return self._default_response('read')

    def can_add(self):  # pragma: no cover
        """By default, everyone can add
        """
        return self._default_response('add')

    def can_delete(self):  # pragma: no cover
        """By default, everyone can delete
        """
        return self._default_response('delete')

    def can_edit(self):  # pragma: no cover
        """By default, everyone can change
        """
        return self._default_response('edit')

    # GENERIC CAPABILITIES
    # --------------------

    def get_user_capabilities(self, method_list=None, capabilities_cache=None):
        if not method_list:
            method_list = []
        if not capabilities_cache:
            capabilities_cache = {}

        if self.instance is None:
            return {}
        user_capabilities = {}

        for method in method_list:
            if method in capabilities_cache:
                user_capabilities[method] = capabilities_cache[method]
                if self.user.is_superuser and not user_capabilities[method]:
                    # Cache override for models with bad orphaned state
                    user_capabilities[method] = True
                continue

            # we could have it map here to similar siblings
            user_capabilities[method] = self.get_method_capability(method)

        return user_capabilities

    def get_method_capability(self, method):
        try:
            access_method = getattr(self, 'can_%s' % method)
            return access_method()
        except (ParseError, ObjectDoesNotExist, PermissionDenied):
            return False
        return False


class GenericDefaultAccess(BaseAccess):
    """Generic default accessor that can be used for less-special models
    """


def register_accessor(access_class, model=None):
    """
    Registers a model accessor as the gatekeeper for actions around a resource type

    @register_access
    class TenantAccess(BaseAccess):
        ...
    """
    model_class = model if model else access_class.model

    if model_class in access_registry:
        raise ValueError(
            f'Two model accessors listed {model_class} as their model: '
            f'{access_class} and {access_registry[model_class]}'
        )

    if not (inspect.isclass(model_class) and issubclass(model_class, Model)):
        raise TypeError('model_class should be a Django model class')

    if not (inspect.isclass(model_class) and issubclass(access_class, BaseAccess)):
        raise TypeError(
            'register_accessor should only be placed on a class definition that subclasses BaseAccess'
        )

    if not access_class.model and model_class:  # can be used with generic access classes
        access_class = type(f'{access_class.__name__}_Wrapper', (access_class,), dict())
        access_class.model = model_class

    access_registry[model_class] = access_class
    return access_class
