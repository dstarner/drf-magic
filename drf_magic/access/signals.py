from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, post_save

from drf_magic.models import ROLE_SUPERUSER, Role


def rebuild_role_ancestor_list(reverse, model, instance, pk_set, action, **kwargs):
    """When a role parent is added or removed, update our role hierarchy list
    """
    if action == 'post_add':
        if reverse:
            model.rebuild_role_ancestor_list(list(pk_set), [])
        else:
            model.rebuild_role_ancestor_list([instance.id], [])

    if action in ['post_remove', 'post_clear']:
        if reverse:
            model.rebuild_role_ancestor_list([], list(pk_set))
        else:
            model.rebuild_role_ancestor_list([], [instance.id])


def sync_superuser_status_to_rbac(instance, **kwargs):
    """
    When the is_superuser flag is changed on a user, reflect that
    in the membership of the System Administrator role
    """
    update_fields = kwargs.get('update_fields', None)
    if update_fields and 'is_superuser' not in update_fields:
        return
    if instance.is_superuser:
        Role.singleton(ROLE_SUPERUSER).members.add(instance)
    else:
        Role.singleton(ROLE_SUPERUSER).members.remove(instance)


post_save.connect(sync_superuser_status_to_rbac, sender=get_user_model())
m2m_changed.connect(rebuild_role_ancestor_list, Role.parents.through)
