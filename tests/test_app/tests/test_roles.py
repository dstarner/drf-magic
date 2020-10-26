from django.contrib.auth.models import User
from django.test import TestCase

from drf_magic.models import ROLE_ADMIN, Role
from tests.test_app.models import SecretRecipe


class BasicModelsTestCase(TestCase):

    def test_user_in_role(self):
        admin_user = User.objects.create_user('admin')
        user = User.objects.create_user('user')
        role = Role.singleton(ROLE_ADMIN)
        role.members.add(admin_user)
        role.save()

        self.assertTrue(admin_user in role)
        self.assertTrue(user not in role)
        self.assertEqual(role.member_count, 1)

    def test_update_member_list_strict(self):
        usernames = {'a', 'b', 'c', 'd'}
        users = {user: User.objects.create_user(user) for user in usernames}
        role = Role.singleton(ROLE_ADMIN)

        before = {'a'}
        not_before = usernames - before
        role.update_member_list(before)
        role.save()
        self.assertTrue(all([users[x] in role for x in before]))
        self.assertTrue(all([users[x] not in role for x in not_before]))

        after = {'c', 'd'}
        not_after = usernames - after
        role.update_member_list(after, strict=True)
        role.save()
        self.assertTrue(all([users[x] in role for x in after]))
        self.assertTrue(all([users[x] not in role for x in not_after]))

    def test_update_member_list_lenient(self):
        usernames = {'a', 'b', 'c', 'd'}
        users = {user: User.objects.create_user(user) for user in usernames}
        role = Role.singleton(ROLE_ADMIN)

        before = {'a'}
        not_before = usernames - before
        role.update_member_list(before)
        role.save()
        self.assertTrue(all([users[x] in role for x in before]))
        self.assertTrue(all([users[x] not in role for x in not_before]))

        after = {'c', 'd'}
        not_after = usernames - after - before
        role.update_member_list(after, strict=False)
        role.save()
        self.assertTrue(all([users[x] in role for x in after | before]))
        self.assertTrue(all([users[x] not in role for x in not_after]))


class PatchTestCase(TestCase):

    def test_user_has_superuser_role(self):
        superuser = User.objects.create_superuser('superuser')
        normal = User.objects.create_user('user')
        unsaved_user = User(username='unsaved')

        self.assertTrue(superuser.has_superuser_role)
        self.assertTrue(superuser.has_superuser_role)  # Checked twice for the cache
        self.assertFalse(normal.has_superuser_role)
        with self.assertRaises(AttributeError):
            unsaved_user.has_superuser_role


class SecretRecipeTestCase(TestCase):

    def setUp(self):
        self.recipe = SecretRecipe.objects.create(name='Test Recipe')

        self.global_admin = User.objects.create_superuser('global-admin')
        self.global_admin_role = Role.singleton(ROLE_ADMIN)
        self.global_admin_role.members.add(self.global_admin)

        self.admin = User.objects.create_user('admin')
        self.recipe.admin.members.add(self.admin)
        self.recipe.admin.save()

        self.member = User.objects.create_user('member')
        self.recipe.member.members.add(self.admin)
        self.recipe.member.save()

    def test_admin_has_member(self):
        self.assertTrue(self.admin in self.recipe.member)

    def test_member_does_not_have_admin(self):
        self.assertTrue(self.member not in self.recipe.admin)

    def test_site_admin_has_admin(self):
        self.assertTrue(self.global_admin in self.recipe.admin)

    def test_site_admin_has_member(self):
        self.assertTrue(self.global_admin in self.recipe.member)

    def test_ancestor_of(self):
        self.assertTrue(self.recipe.admin.is_ancestor_of(self.recipe.member))

    def test_counts(self):
        self.assertEqual(self.global_admin_role.member_count, 1)
        self.assertEqual(self.global_admin_role.permissioned_count, 1)

        self.assertEqual(self.recipe.admin.member_count, 1)
        self.assertEqual(self.recipe.admin.permissioned_count, 2)

        self.assertEqual(self.recipe.member.member_count, 1)
        self.assertEqual(self.recipe.member.permissioned_count, 3)

    # def test_visible_roles(self):
    #     default_roles = [Role.singleton(x) for x in _DEFAULT_ROLES]
    #     self.assertEqual(set(Role.visible_roles(self.global_admin)), set(default_roles + [
    #         self.recipe.admin,
    #         self.recipe.member
    #     ]))

    #     self.assertEqual(Role.visible_roles(self.admin), [self.recipe.member])

    def test_admin_role_name(self):
        pass

    def test_admin_role_description(self):
        pass
