import logging

import frontmatter
import inflection
from django.conf import settings
from drf_yasg2 import openapi
from drf_yasg2.inspectors import SwaggerAutoSchema
from drf_yasg2.utils import get_serializer_ref_name
from drf_yasg2.views import get_schema_view
from rest_framework import permissions
from rest_framework.utils import formatting

from drf_magic.serializers import WritableNestedSerializer

logger = logging.getLogger(__name__)


class SmartSummaryAutoSchema(SwaggerAutoSchema):
    """
    Turns the operation_id / name for each API endpoint in the Swagger documentation
    to replace underscores ('_') with spaces (' '), titlize the result, and to replace
    certain defined substrings
    """

    title_overrides = {
        'token_refresh_create': 'Refresh Token',
        'token_verify_create': 'Verify Token'
    }

    # at the end, replace any instance of key with the value
    replacers = {
        'Jwt': 'JWT',
        'Pvf': 'PVF',
    }

    writable_serializers = {}

    def get_request_serializer(self):
        """
        This is designed to find all of the WritableNestedSerializers and post requests to
        make it so that it will look up the primary keys
        """
        serializer = super().get_request_serializer()
        if serializer is not None and self.method in self.implicit_body_methods:
            properties = {}
            for child_name, child in serializer.fields.items():
                if isinstance(child, (WritableNestedSerializer,)):
                    properties[child_name] = None

            if properties:
                if type(serializer) not in self.writable_serializers:  # pylint: disable=unidiomatic-typecheck
                    writable_name = 'Writable' + type(serializer).__name__
                    meta_class = getattr(type(serializer), 'Meta', None)
                    if meta_class:
                        ref_name = 'Writable' + get_serializer_ref_name(serializer)
                        writable_meta = type('Meta', (meta_class,), {'ref_name': ref_name})
                        properties['Meta'] = writable_meta

                    self.writable_serializers[type(serializer)] = type(writable_name, (type(serializer),), properties)

                writable_class = self.writable_serializers[type(serializer)]
                serializer = writable_class()

        return serializer

    def get_value(self, metadata, key, default=None):
        """Returns the value either from the metadata or from the view
        """
        if key in metadata:
            return metadata[key]
        return getattr(self.view, key, default)

    def get_format_kwargs(self):
        format_kwargs = {}
        model = getattr(self.view, 'model', None)
        if model:
            meta = model._meta
            for attr in ['verbose_name', 'verbose_name_plural']:
                format_kwargs[attr] = getattr(meta, attr)
        parent_view = self.view.parent_view() if hasattr(self.view, 'parent_viewset') else None
        parent_model = None if not parent_view else getattr(parent_view, 'model', None)
        if parent_model:
            meta = parent_model._meta
            for attr in ['verbose_name', 'verbose_name_plural']:
                format_kwargs[f'parent_{attr}'] = getattr(meta, attr)
        return format_kwargs

    def get_title(self, metadata=None):
        """Will return the full title / summary of the operation
        """
        if not metadata:
            metadata = {}
        operation_keys = self.operation_keys.copy()
        verb = operation_keys.pop()
        noun = operation_keys.pop()
        short_title = self.get_value(metadata, 'title', None)
        if not short_title:
            short_title = self.title_overrides.get(self.get_operation_id(), None)
            if not short_title:
                short_title = f'{verb} {noun}'

        short_title = short_title.format(**self.get_format_kwargs())

        category_start = self.get_value(metadata, 'category_start', None)
        index_to_start_with = int(self.get_value(metadata, 'category_start_idx', 0))
        try:
            if category_start:
                index_to_start_with = operation_keys.index(category_start)
        except ValueError:
            pass

        operation_keys = operation_keys[index_to_start_with:]
        categories = ' > '.join(operation_keys) if len(operation_keys) > 1 else None
        title = ': '.join(filter(lambda x: x, [short_title, categories]))
        return inflection.titleize(title)

    def get_metadata_content_tuple(self):
        """Tries to load the frontmatter data and content for the current action type for the operation
        """
        view_docs = formatting.dedent(self.view.__doc__)

        docs = list(map(lambda x: f'---{x}', view_docs.split('===')[1:]))
        method = self.method
        action = getattr(self.view, 'action_map', {}).get(method.lower(), None) if self.view.action_map else None
        for doc_bloc in docs:
            metadata, content = frontmatter.parse(doc_bloc)
            if not metadata:
                continue
            action_to_map = metadata.get('action', 'default')
            if action_to_map == action or (isinstance(action_to_map, list) and action in action_to_map):
                return metadata, content
        if action and hasattr(self.view, action):
            action_func = getattr(self.view, action, None)
            action_docs = formatting.dedent(action_func.__doc__)
            if '===' in action_docs:
                metadata, content = frontmatter.parse(action_docs.replace('===', '---'))
                return metadata, content
            return None, action_docs
        return None, view_docs

    def get_summary_and_description(self):  # pragma: no cover
        """Creates the summary and description. The following are available per action
        """
        metadata, desc = self.get_metadata_content_tuple()
        return self.get_title(metadata), desc.format(**self.get_format_kwargs())


configuration = settings.YASG_SCHEMA

description = ''
with open(configuration['DESCRIPTION_PATH'], 'r') as f:
    description = f.read()

contact = configuration.get('CONTACT', None)
logo = configuration.get('LOGO', None)

# Used to generate the Swagger / ReDoc documentation automatically
SchemaView = get_schema_view(
    openapi.Info(
        title=configuration['TITLE'],
        default_version=configuration['VERSION'],
        description=description,
        contact=None if not contact else (
            openapi.Contact(
                name=contact['NAME'],
                email=contact['EMAIL']
            )
        ),
        x_logo=None if not logo else {
            'url': logo['SRC'],
            'backgroundColor': '#fafafa',
            'altText': configuration['TITLE'],
            'href': logo['URL'],
        }
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
