from django.db import models

from drf_magic.fields import ImplicitRoleField
from drf_magic.models import ROLE_ADMIN


class Person(models.Model):

    first_name = models.CharField(max_length=64, default='')

    last_name = models.CharField(max_length=64, default='')

    occupation = models.CharField(max_length=128, default='programmer')

    class Meta:
        ordering = ['last_name']


class GrandParent(models.Model):

    gp_value = models.IntegerField(default=0)


class Parent(models.Model):

    grand_parent = models.ForeignKey(GrandParent, related_name='parents', on_delete=models.CASCADE)

    p_value = models.IntegerField(default=0)


class Child(models.Model):

    parent = models.ForeignKey(Parent, related_name='children', on_delete=models.CASCADE)

    c_value = models.IntegerField(default=0)


class SecretRecipe(models.Model):

    name = models.CharField(max_length=64, default='')

    admin = ImplicitRoleField(parent_role='singleton:'+ROLE_ADMIN)

    member = ImplicitRoleField(parent_role='admin')
