from .access.accessors import register_accessor  # noqa


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
