"""
This patches the Django user class to use our permission accessors instead of its own
"""
from django.contrib.auth import get_user_model

from drf_magic.models import ROLE_SUPERUSER

from .accessors import check_user_access

User = get_user_model()
User.add_to_class('can_access', check_user_access)


@property
def user_has_superuser_role(user):
    """Return if a user is a site-wide system administrator
    """
    if not hasattr(user, '_has_superuser_role'):
        if user.pk:
            user._has_superuser_role = user.roles.filter(
                singleton_name=ROLE_SUPERUSER,
                role_field=ROLE_SUPERUSER
            ).exists()
        else:
            # Odd case where user is unsaved, this should never be relied on
            raise AttributeError('User must have pk to check if superuser')
    return user._has_superuser_role


User.add_to_class('has_superuser_role', user_has_superuser_role)
