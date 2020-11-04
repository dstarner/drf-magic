import os

from pip._internal.req import parse_requirements
from setuptools import setup, find_packages

import drf_magic

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
REQUIREMENTS_PATH = 'requirements.txt'


# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Parse out requirements
install_reqs = parse_requirements(REQUIREMENTS_PATH, session='build')
reqs = [str(ir.requirement) for ir in install_reqs]


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
    install_requires=reqs
)
