import logging

from drf_yasg2.generators import OpenAPISchemaGenerator
from rest_framework.settings import api_settings

logger = logging.getLogger(__name__)


def _is_iterable(value):
    try:
        iter(value)
    except TypeError:
        return False
    return True


class VersionAgnosticSchemaGenerator(OpenAPISchemaGenerator):  # pragma: no cover
    """
    This will build the documentation sections without including the
    v1 or v2 at the beginning of a URL
    """

    def get_operation_keys(self, subpath, method, view):
        operation_keys = super().get_operation_keys(subpath, method, view)
        allowed_versions = ([api_settings.DEFAULT_VERSION] + api_settings.ALLOWED_VERSIONS)
        needs_checked = True
        while needs_checked:
            if not operation_keys:
                needs_checked = False
            elif (operation_keys[0] in allowed_versions) or operation_keys[0].lower() == 'api':
                operation_keys = operation_keys[1:]
            else:
                needs_checked = False
        return operation_keys

    def get_categories(self, view, operation=None):
        """Returns the categories that the view / operation
        """
        tags = operation.tags if operation else []
        if hasattr(view, 'categories') and _is_iterable(view.categories):
            tags = view.categories
        if hasattr(view, 'doc_category_from_parent') and view.doc_category_from_parent:
            parent = view.parent_view()
            tags = self.get_categories(parent, operation)
        elif hasattr(view, 'model') and view.model:
            tags = [view.model._meta.verbose_name_plural.replace(' ', '-').lower()]
        else:
            logger.debug('%s has no model or categories defined, so doc section is defaulted.', type(view).__name__)
        return tags

    def get_operation(self, view, path, prefix, method, components, request):
        operation = super().get_operation(view, path, prefix, method, components, request)
        operation.tags = self.get_categories(view, operation)
        return operation
