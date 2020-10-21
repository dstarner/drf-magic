import os
import sys

import django
from django.core import management


def pytest_addoption(parser):
    parser.addoption('--no-pkgroot', action='store_true', default=False,
                     help='Remove package root directory from sys.path, ensuring that '
                          'drf_magic is imported from the installed site-packages. '
                          'Used for testing the distribution.')
    parser.addoption('--staticfiles', action='store_true', default=False,
                     help='Run tests with static files collection, using manifest '
                          'staticfiles storage. Used for testing the distribution.')


def pytest_configure(config):
    from django.conf import settings
    from django.test.runner import DiscoverRunner

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    "debug": True,  # We want template errors to raise
                }
            },
        ],
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'drf_magic',
            'tests',
            'tests.test_app',
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ),
    )

    # guardian is optional
    try:
        import guardian  # NOQA
    except ImportError:
        pass
    else:
        settings.ANONYMOUS_USER_ID = -1
        settings.AUTHENTICATION_BACKENDS = (
            'django.contrib.auth.backends.ModelBackend',
            'guardian.backends.ObjectPermissionBackend',
        )
        settings.INSTALLED_APPS += (
            'guardian',
        )

    if config.getoption('--no-pkgroot'):
        sys.path.pop(0)

        # import drf_magic before pytest re-adds the package root directory.
        import drf_magic
        package_dir = os.path.join(os.getcwd(), 'drf_magic')
        assert not drf_magic.__file__.startswith(package_dir)

    # Manifest storage will raise an exception if static files are not present (ie, a packaging failure).
    if config.getoption('--staticfiles'):
        import drf_magic
        settings.STATIC_ROOT = os.path.join(os.path.dirname(drf_magic.__file__), 'static-root')
        settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

    django.setup()

    runner = DiscoverRunner()
    runner.setup_test_environment()
    runner.setup_databases()

    if config.getoption('--staticfiles'):
        management.call_command('collectstatic', verbosity=0, interactive=False)
