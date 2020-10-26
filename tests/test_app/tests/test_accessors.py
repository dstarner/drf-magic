from django.contrib.auth import get_user_model
from django.test import TestCase

from drf_magic.access import (
    GenericDefaultAccess, accessors, check_user_access, instance_to_accessor
)
from drf_magic.decorators import register_accessor

from ..models import Person


class PersonAccessorTestCase(TestCase):

    def tearDown(self):
        accessors.access_registry = {}

    def test_instance_to_accessor(self):
        person = Person(first_name='Bill', last_name='Gate', occupation='software_engineer')
        register_accessor(GenericDefaultAccess, Person)
        self.assertTrue(issubclass(instance_to_accessor(person), GenericDefaultAccess))

    def test_double_register(self):
        register_accessor(GenericDefaultAccess, Person)
        with self.assertRaises(ValueError):
            register_accessor(GenericDefaultAccess, Person)

    def test_no_register(self):
        person = Person(first_name='Bill', last_name='Gate', occupation='software_engineer')
        self.assertIsNone(instance_to_accessor(person))

    def test_simple_check_user_access(self):
        should_allow = True
        _self = self
        person = Person(first_name='Bill', last_name='Gate', occupation='software_engineer')
        user = get_user_model().objects.create_user('test@test.com')

        @register_accessor
        class PersonAccessor(accessors.BaseAccess):
            model = Person

            def can_do_a_thing(self):
                _self.assertEqual(self.instance, person)
                return should_allow

        actual = check_user_access(user, Person, 'do_a_thing', instance=person)
        self.assertEqual(should_allow, actual)

    def test_simple_check_user_access_disallow(self):
        should_allow = False
        _self = self
        user = get_user_model().objects.create_user('test@test.com')
        person = Person(first_name='Bill', last_name='Gate', occupation='software_engineer')

        @register_accessor
        class PersonAccessor(accessors.BaseAccess):
            model = Person

            def can_do_a_thing(self):
                _self.assertEqual(self.instance, person)
                return should_allow

        actual = check_user_access(user, person, 'do_a_thing')
        self.assertEqual(should_allow, actual)

    def test_allow_on_missing_accessor(self):
        user = get_user_model().objects.create_user('test@test.com')
        person = Person(first_name='Bill', last_name='Gate', occupation='software_engineer')
        should_allow = True
        with self.settings(**{
            'DRF_MAGIC': {
                'ALLOW_ON_MISSING_ACCESSOR': should_allow
            }
        }):
            actual = check_user_access(user, person, 'do_a_thing')
        self.assertEqual(should_allow, actual)

    def test_disallow_on_missing_accessor(self):
        user = get_user_model().objects.create_user('test@test.com')
        person = Person(first_name='Bill', last_name='Gate', occupation='software_engineer')
        should_allow = False
        with self.settings(**{
            'DRF_MAGIC': {
                'ALLOW_ON_MISSING_ACCESSOR': should_allow
            }
        }):
            actual = check_user_access(user, person, 'do_a_thing')
        self.assertEqual(should_allow, actual)
