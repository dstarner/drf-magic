import os

from pip._internal.req import parse_requirements
from setuptools import setup, find_packages

import drf_magic

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


setup(
    name=drf_magic.__package__,
    version=drf_magic.__version__,
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    license=drf_magic.__license__,
    description=drf_magic.__docs__,
    long_description=README,
    long_description_content_type='text/markdown',
    url=drf_magic.__url__,
    author=drf_magic.__author__,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content'
    ],
    install_requires=[
        'Django>=3.0.0',
        'django-admin-list-filter-dropdown>=1.0.3',
        'django-filter>=2.4.0',
        'djangorestframework>=3.0.0',
        'drf-nested-routers>=0.92.0',
        'drf-yasg2==1.19.3',
        'python-frontmatter==0.5.0',
        'inflection>=0.5.1'
    ]
)
