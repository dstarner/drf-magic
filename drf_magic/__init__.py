from .apps import MagicAppConfig

__all__ = [
    'MagicAppConfig',
]


__title__ = 'Django REST Framework Magic'
__package__ = 'django-rest-magic'
__docs__ = 'Increased functionality across permissions, serializers, viewsets, and more.'
__version__ = '1.0.0'
__author__ = 'Dan Starner'
__license__ = 'BSD 3-Clause'
__url__ = 'https://github.com/dstarner/drf-magic'

default_app_config = 'drf_magic.apps.DRFMagicConfig'

# Version synonym
VERSION = __version__