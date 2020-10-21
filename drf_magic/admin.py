from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.db.models import Q
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, RelatedDropdownFilter
)

from .models import SINGLETON_ROLES, Role


class RoleInline(GenericStackedInline):
    """Allows displaying the associated roles with a controlled resource in it's admin page
    """

    model = Role
    extra = 0
    # TODO: list_filter of role name and singleton or not
    filter_horizontal = ('members', 'parents')
    exclude = ('implicit_parents', 'singleton_name')


class SingletonListFilter(admin.SimpleListFilter):
    """Used to filter global singleton roles or resource-scoped roles
    """

    title = 'Variant'
    parameter_name = 'variant'

    SINGLETON = ('global', 'Global Singleton')
    SCOPED = ('scoped', 'Scoped to Resource')

    def lookups(self, request, model_admin):
        return [self.SINGLETON, self.SCOPED]

    def queryset(self, request, queryset):
        method = None
        if self.value() == self.SINGLETON[0]:
            method = queryset.filter
        elif self.value() == self.SCOPED[0]:
            method = queryset.exclude
        else:
            return queryset

        return method(Q(role_field__in=SINGLETON_ROLES) | Q(singleton_name__in=SINGLETON_ROLES))


class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'description', 'key', 'is_singleton',
        'content_object', 'member_count', 'permissioned_count'
    )
    list_filter = (
        ('content_type', RelatedDropdownFilter),
        ('role_field', DropdownFilter),
        SingletonListFilter,
    )
    filter_horizontal = ('members',)
    exclude = ('implicit_parents',)

    def get_form(self, request, obj=None, change=False, **kwargs):
        """For singletons, show the singleton_name field instead of role_field
        """
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        if obj.is_singleton:
            self.exclude = self.exclude + ('role_field',)
            form.base_fields['singleton_name'].required = True
        return form
