import os
import shutil
import sys

import django
from django.core import management

TEST_PREFIX = 'tests'
test_apps = [
    'test_app',
]


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
        ) + tuple(map(lambda x: f'{TEST_PREFIX}.{x}', test_apps)),
        SWAGGER_SETTINGS={
            'DEFAULT_GENERATOR_CLASS': 'drf_magic.docs.generators.VersionAgnosticSchemaGenerator',
            'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_magic.docs.schema.SmartSummaryAutoSchema',
        },
        YASG_SCHEMA={
            'TITLE': 'Test Docs',
            'VERSION': '0.1.0',
            'DESCRIPTION_PATH': os.path.join(os.path.dirname(__file__), 'dummy_api_desc.md'),
        },
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ),
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

    for app in test_apps:
        management.call_command('makemigrations', app)

    runner = DiscoverRunner()
    runner.setup_test_environment()
    runner.setup_databases()

    if config.getoption('--staticfiles'):
        management.call_command('collectstatic', verbosity=0, interactive=False)


def pytest_unconfigure():
    for app in test_apps:
        migrations_path = os.path.join(TEST_PREFIX, app, 'migrations')
        shutil.rmtree(migrations_path, ignore_errors=True)
