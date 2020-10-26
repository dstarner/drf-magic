from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models

from . import Role, RoleAncestorEntry, get_roles_on_resource


class RoleManagedModelMixin(models.Model):
    """Mixin to add onto models that can be controlled by roles.
    This adds some useful methods to the model instances and generic class that perform lookups
    """

    class Meta:
        abstract = True

    def get_permissions(self, accessor):
        """
        Returns a string list of the roles a accessor has for a given resource.
        An accessor can be either a User, Role, or an arbitrary resource that
        contains one or more Roles associated with it.
        """
        return get_roles_on_resource(self, accessor)

    @classmethod
    def accessible_objects(cls, accessor, role_field):
        """
        Use instead of `MyModel.objects` when you want to only consider
        resources that a user has specific permissions for. For example:
        MyModel.accessible_objects(user, 'read_role').filter(name__istartswith='bar');
        NOTE: This should only be used for list type things. If you have a
        specific resource you want to check permissions on, it is more
        performant to resolve the resource in question then call
        `myresource.get_permissions(user)`.
        """
        return cls.objects.filter(pk__in=cls.accessible_pk_qs(accessor, role_field))

    @classmethod
    def scope_accessible_queryset(cls, queryset, accessor, role_field):
        """
        Scopes a given queryset when you want to only consider
        resources that a user has specific permissions for. For example:
        MyModel.accessible_objects(user, 'read_role').filter(name__istartswith='bar');
        NOTE: This should only be used for list type things. If you have a
        specific resource you want to check permissions on, it is more
        performant to resolve the resource in question then call
        `myresource.get_permissions(user)`.
        """
        return queryset.filter(pk__in=cls.accessible_pk_qs(accessor, role_field))

    @classmethod
    def accessible_pk_qs(cls, accessor, role_field, content_types=None):
        """
        Returns a list of primary keys for objects that the accessor has the role represented by 'role_field'
        for. This also accounts for role hierarchy due to the layout of the RoleAncestorEntry table

        This means for example:

        If user 'dcuser' has the 'read_role' role for resource with a primary key of 2 then
            `accessible_pk_qs(dcuser, 'read_role') --> [2]`
        """
        if isinstance(accessor, get_user_model()):
            ancestor_roles = accessor.roles.all()
        elif isinstance(accessor, Role):
            ancestor_roles = [accessor]
        else:
            accessor_type = ContentType.objects.get_for_model(accessor)
            ancestor_roles = Role.objects.filter(content_type__pk=accessor_type.id, object_id=accessor.id)

        if content_types is None:
            ct_kwarg = dict(content_type_id=ContentType.objects.get_for_model(cls).id)
        else:
            ct_kwarg = dict(content_type_id__in=content_types)

        return RoleAncestorEntry.objects.filter(
            ancestor__in=ancestor_roles,
            role_field=role_field,
            **ct_kwarg
        ).values_list('object_id').distinct()
