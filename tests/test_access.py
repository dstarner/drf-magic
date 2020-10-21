from django.contrib.auth import get_user_model
from django.test import TestCase

from drf_magic.access.accessors import BaseAccess
from drf_magic.decorators import check_superuser

User = get_user_model()


class SuperuserAccessTests(TestCase):

    def setUp(self):
        User.objects.create_user('superuser-tests', 'test@test.com')

    def test_superuser(self):
        class Accessor(BaseAccess):

            def can_add(self):
                return 'bar'  # pragma: no cover

        user = User.objects.get(username='superuser-tests')
        user.is_superuser = True
        user.save()
        access = Accessor(user)

        can_add = check_superuser(Accessor.can_add)
        self.assertTrue(can_add(access))

    def test_not_superuser(self):

        class Accessor(BaseAccess):

            def can_add(self):
                return 'boo'

        user = User.objects.get(username='superuser-tests')
        access = Accessor(user)

        can_add = check_superuser(Accessor.can_add)
        self.assertEqual(can_add(access), 'boo')


class GetUserCapabilitiesTestCase(TestCase):

    def test_user_capabilities_method(self):
        """Unit test to verify that the user_capabilities method will defer
        to the appropriate sub-class methods of the access classes.
        Note that normal output is True/False, but a string is returned
        in these tests to establish uniqueness.
        """

        class FooAccess(BaseAccess):
            def can_change(self):
                return 'bar'

            def can_copy(self):
                return 'foo'

        user = User(username='auser')
        foo = object()
        foo_access = FooAccess(user, instance=foo)
        foo_capabilities = foo_access.get_user_capabilities(method_list=['change', 'copy'])
        self.assertEqual(foo_capabilities, {
            'change': 'bar',
            'copy': 'foo'
        })
