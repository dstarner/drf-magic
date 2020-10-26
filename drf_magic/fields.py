import json

from django.apps import apps
from django.db import models
from django.db.models.fields.related import lazy_related_operation
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor, ManyToManyDescriptor,
    ReverseManyToOneDescriptor, create_forward_many_to_many_manager
)
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.utils.encoding import force_str
from django.utils.functional import cached_property

from .models import Role, batch_role_ancestor_rebuilding


def resolve_role_field(obj, field):
    ret = []
    field_components = field.split('.', 1)
    if hasattr(obj, field_components[0]):
        obj = getattr(obj, field_components[0])
    else:
        return []

    if obj is None:
        return []

    if len(field_components) == 1:
        role_cls = apps.get_model('drf_magic', 'Role')
        if not isinstance(obj, role_cls):
            raise Exception(force_str('{} refers to a {}, not a Role'.format(field, type(obj))))
        ret.append(obj.id)
    else:
        if isinstance(obj, ManyToManyDescriptor):
            for o in obj.all():
                ret += resolve_role_field(o, field_components[1])
        else:
            ret += resolve_role_field(obj, field_components[1])
    return ret


def update_role_parentage_for_instance(instance):
    """
    updates the parents listing for all the roles
    of a given instance if they have changed
    """
    for implicit_role_field in getattr(instance.__class__, '__implicit_role_fields'):
        cur_role = getattr(instance, implicit_role_field.name)
        original_parents = set(json.loads(cur_role.implicit_parents))
        new_parents = implicit_role_field._resolve_parent_roles(instance)
        cur_role.parents.remove(*list(original_parents - new_parents))
        cur_role.parents.add(*list(new_parents - original_parents))
        new_parents_list = list(new_parents)
        new_parents_list.sort()
        new_parents_json = json.dumps(new_parents_list)
        if cur_role.implicit_parents != new_parents_json:
            cur_role.implicit_parents = new_parents_json
            cur_role.save()


class ImplicitRoleDescriptor(ForwardManyToOneDescriptor):
    pass


class ImplicitRoleField(models.ForeignKey):
    """Implicitly creates a role entry for a resource

    Im not going to lie, this was ripped directly from AWX
    """

    def __init__(self, *args, parent_role=None, **kwargs):
        self.parent_role = parent_role

        kwargs.setdefault('to', 'drf_magic.Role')
        kwargs.setdefault('related_name', '+')
        kwargs.setdefault('null', 'True')
        kwargs.setdefault('editable', False)
        kwargs.setdefault('on_delete', models.CASCADE)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['parent_role'] = self.parent_role
        return name, path, args, kwargs

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        setattr(cls, self.name, ImplicitRoleDescriptor(self))

        if not hasattr(cls, '__implicit_role_fields'):
            setattr(cls, '__implicit_role_fields', [])
        getattr(cls, '__implicit_role_fields').append(self)

        post_save.connect(self._post_save, cls, True, dispatch_uid='implicit-role-post-save')
        post_delete.connect(self._post_delete, cls, True, dispatch_uid='implicit-role-post-delete')

        function = lambda local, related, field: self.bind_m2m_changed(field, related, local)  # noqa
        lazy_related_operation(function, cls, 'self', field=self)

    def bind_m2m_changed(self, _self, _role_class, cls):
        if not self.parent_role:
            return

        field_names = self.parent_role
        if not isinstance(field_names, list):
            field_names = [field_names]

        for field_name in field_names:
            # Handle the OR syntax for role parents
            if isinstance(field_name, tuple):
                continue

            if isinstance(field_name, bytes):
                field_name = field_name.decode('utf-8')

            if field_name.startswith('singleton:'):
                continue

            field_name, _, field_attr = field_name.partition('.')
            field = getattr(cls, field_name)

            if isinstance(field, (ReverseManyToOneDescriptor, ManyToManyDescriptor)):
                if '.' in field_attr:
                    raise Exception('Referencing deep roles through ManyToMany fields is unsupported.')

                if isinstance(field, ReverseManyToOneDescriptor):
                    sender = field.through
                else:
                    sender = field.related.through

                reverse = isinstance(field, ManyToManyDescriptor)
                m2m_changed.connect(self.m2m_update(field_attr, reverse), sender, weak=False)

    def m2m_update(self, field_attr, _reverse):
        def _m2m_update(instance, action, model, pk_set, reverse, **kwargs):
            if action in ['post_add', 'pre_remove']:
                if _reverse:
                    reverse = not reverse

                if reverse:
                    for pk in pk_set:
                        obj = model.objects.get(pk=pk)
                        if action == 'post_add':
                            getattr(instance, field_attr).children.add(getattr(obj, self.name))
                        if action == 'pre_remove':
                            getattr(instance, field_attr).children.remove(getattr(obj, self.name))

                else:
                    for pk in pk_set:
                        obj = model.objects.get(pk=pk)
                        if action == 'post_add':
                            getattr(instance, self.name).parents.add(getattr(obj, field_attr))
                        if action == 'pre_remove':
                            getattr(instance, self.name).parents.remove(getattr(obj, field_attr))
        return _m2m_update

    def _post_save(self, instance, created, *args, **kwargs):
        Role_ = apps.get_model('drf_magic', 'Role')
        ContentType_ = apps.get_model('contenttypes', 'ContentType')
        ct_id = ContentType_.objects.get_for_model(instance).id

        Model = apps.get_model(instance._meta.app_label, instance.__class__.__name__)
        latest_instance = Model.objects.get(pk=instance.pk)

        with batch_role_ancestor_rebuilding():
            # Create any missing role objects
            missing_roles = []
            for implicit_role_field in getattr(latest_instance.__class__, '__implicit_role_fields'):
                cur_role = getattr(latest_instance, implicit_role_field.name, None)
                if cur_role is None:
                    missing_roles.append(
                        Role_(
                            role_field=implicit_role_field.name,
                            content_type_id=ct_id,
                            object_id=latest_instance.id
                        )
                    )

            if len(missing_roles) > 0:
                Role_.objects.bulk_create(missing_roles)
                updates = {}
                role_ids = []
                for role in Role_.objects.filter(content_type_id=ct_id, object_id=latest_instance.id):
                    setattr(latest_instance, role.role_field, role)
                    updates[role.role_field] = role.id
                    role_ids.append(role.id)
                type(latest_instance).objects.filter(pk=latest_instance.pk).update(**updates)
                Role.rebuild_role_ancestor_list(role_ids, [])

            update_role_parentage_for_instance(latest_instance)
            instance.refresh_from_db()

    def _resolve_parent_roles(self, instance):
        if not self.parent_role:
            return set()

        paths = self.parent_role if isinstance(self.parent_role, list) else [self.parent_role]
        parent_roles = set()

        for path in paths:
            if path.startswith('singleton:'):
                singleton_name = path[10:]
                Role_ = apps.get_model('drf_magic', 'Role')
                qs = Role_.objects.filter(singleton_name=singleton_name)
                if qs.count() >= 1:
                    role = qs[0]
                else:
                    role = Role_.objects.create(singleton_name=singleton_name, role_field=singleton_name)
                parents = [role.id]
            else:
                parents = resolve_role_field(instance, path)

            for parent in parents:
                parent_roles.add(parent)
        return parent_roles

    def _post_delete(self, instance, *args, **kwargs):
        role_ids = []
        for implicit_role_field in getattr(instance.__class__, '__implicit_role_fields'):
            role_ids.append(getattr(instance, implicit_role_field.name + '_id'))

        Role_ = apps.get_model('drf_magic', 'Role')
        child_ids = list(Role_.parents.through.objects.filter(
            to_role_id__in=role_ids
        ).distinct().values_list('from_role_id', flat=True))

        Role_.objects.filter(id__in=role_ids).delete()
        Role.rebuild_role_ancestor_list([], child_ids)


class OrderedManyToManyDescriptor(ManyToManyDescriptor):
    """
    Django doesn't seem to support:
    class Meta:
        ordering = [...]
    ...on custom through= relations for ManyToMany fields.
    Meaning, queries made _through_ the intermediary table will _not_ apply an
    ORDER_BY clause based on the `Meta.ordering` of the intermediary M2M class
    (which is the behavior we want for "ordered" many to many relations):
    https://github.com/django/django/blob/stable/1.11.x/django/db/models/fields/related_descriptors.py#L593
    This descriptor automatically sorts all queries through this relation
    using the `position` column on the M2M table.
    """

    @cached_property
    def related_manager_cls(self):
        model = self.rel.related_model if self.reverse else self.rel.model

        def add_custom_queryset_to_many_related_manager(many_related_manage_cls):
            class OrderedManyRelatedManager(many_related_manage_cls):
                def get_queryset(self):
                    return super(OrderedManyRelatedManager, self).get_queryset().order_by(
                        '%s__position' % self.through._meta.model_name
                    )

            return OrderedManyRelatedManager

        return add_custom_queryset_to_many_related_manager(
            create_forward_many_to_many_manager(
                model._default_manager.__class__,
                self.rel,
                reverse=self.reverse,
            )
        )


class OrderedManyToManyField(models.ManyToManyField):
    """
    A ManyToManyField that automatically sorts all querysets
    by a special `position` column on the M2M table
    """

    def _update_m2m_position(self, sender, **kwargs):
        if kwargs.get('action') in ('post_add', 'post_remove'):
            order_with_respect_to = None
            for field in sender._meta.local_fields:
                if isinstance(field, models.ForeignKey) and isinstance(kwargs['instance'], field.related_model):
                    order_with_respect_to = field.name
            for i, ig in enumerate(sender.objects.filter(**{order_with_respect_to: kwargs['instance'].pk})):
                if ig.position != i:
                    ig.position = i
                    ig.save()

    def contribute_to_class(self, cls, name, **kwargs):
        super(OrderedManyToManyField, self).contribute_to_class(cls, name, **kwargs)
        setattr(
            cls, name,
            OrderedManyToManyDescriptor(self.remote_field, reverse=False)
        )

        through = getattr(cls, name).through
        if isinstance(through, str) and '.' not in through:
            # support lazy loading of string model names
            through = '.'.join([cls._meta.app_label, through])
        m2m_changed.connect(
            self._update_m2m_position,
            sender=through
        )
