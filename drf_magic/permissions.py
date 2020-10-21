import logging

from rest_framework import permissions
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied

logger = logging.getLogger(__name__)


class ModelAccessPermission(permissions.BasePermission):
    """
    Default permissions class to check user access based on the model and
    request method, optionally verifying the request data.

    Viewsets / Views can have the following attributes that will be applied.
    - action: Enforces a special permission role on a view. This is set by default on viewsets
    """

    # Map of the common Django Rest Framework viewset actions to our accessor actions
    drf_action_map = {
        'retrieve': 'read',
        'list': 'list',
        'partial_update': 'change',
        'update': 'edit',
        'create': 'add',
        'delete': 'delete',  # just for the sake of having it here
    }

    # Mapping of default request methods to our accessor actions
    method_action_map = {
        'delete': 'delete',
        'post': 'add',
        'get': 'read',
        'head': 'read',
        'options': 'read',
        'put': 'edit',
        'patch': 'edit'
    }

    def get_checkable_action(self, request, view):
        """
        Grabs the appropriate action name from the view or request so that it
        can be passed to the ModelAccessor
        """
        action = getattr(view, 'action', self.method_action_map[request.method.lower()])
        return self.drf_action_map.get(action, action)

    def check_permissions(self, request, view, obj=None):
        """
        Perform basic permissions checking before delegating to the appropriate
        method based on the request method.
        """
        # Don't allow anonymous users. 401, not 403, hence no raised exception.
        if not request.user or request.user.is_anonymous:
            return False

        # Check if view supports the request method before checking permission
        # based on request method.
        if request.method.upper() not in view.allowed_methods:
            raise MethodNotAllowed(request.method)

        action = self.get_checkable_action(request, view)
        if not obj and action == 'list':  # when listing, we don't have access to the object
            return True                   # so the accessor scoped_queryset will have to work instead

        return view.check_view_permission(request, request.parser_context['kwargs'], action)

    def has_permission(self, request, view, obj=None):
        logger.debug('has_permission(user=%s method=%s data=%r, view=%s, action=%s, obj=%r)',
                     request.user, request.method, request.data,
                     view.__class__.__name__, self.get_checkable_action(request, view), obj)
        try:
            response = self.check_permissions(request, view, obj)
        except PermissionDenied:
            return False
        except Exception as e:
            logger.debug('has_permission raised %r', e, exc_info=True)
            raise
        else:
            logger.debug('has_permission returned %r', response)
            return response

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view, obj)
