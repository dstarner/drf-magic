import inspect

from django.db.models import Model

from .access.accessors import BaseAccess, access_registry


def check_superuser(func):
    """
    check_superuser is a decorator that provides a simple short circuit
    for access checks. If the User object is a superuser, return True, otherwise
    execute the logic of the can_access method.
    """
    def wrapper(self):
        if self.user.is_superuser:
            return True
        return func(self)
    return wrapper


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
