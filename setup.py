import os

from setuptools import setup

import drf_magic

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
 

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))
 

setup(
    name = drf_magic.__package__,
    version = drf_magic.__version__,
    packages = ['drf_magic'],
    include_package_data = True,
    license = drf_magic.__license__,
    description = drf_magic.__docs__,
    long_description = README,
    url = drf_magic.__url__,
    author = drf_magic.__author__,
    classifiers =[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License', # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content'
    ]
)