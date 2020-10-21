from django.urls import path, re_path

from .schema import SchemaView

urlpatterns = [
    # Documentation Routes
    # - - - - - - - - - - - - -
    re_path(
        r'^swagger(?P<format>\.json|\.yaml)$',
        SchemaView.without_ui(cache_timeout=0),
        name='schema-json'
    ),
    path(
        'swagger/',
        SchemaView.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    path('redoc/', SchemaView.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', SchemaView.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
