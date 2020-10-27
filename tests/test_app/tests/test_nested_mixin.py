from django.test import TestCase
from rest_framework.test import APIRequestFactory

from drf_magic.test import NestedRouteTestCaseMixin

from .. import models, views


class AutoNestedRouterViewsetMixinTestCase(TestCase, NestedRouteTestCaseMixin):

    def test_build_parent_filter_context(self):
        child_vs = views.ChildViewSet
        parent_vs = views.ParentViewSet
        gp_vs = views.GrandParentViewSet

        view_class = self.wrap_with_parents(child_vs, parent_vs)
        parent_filters = view_class.build_parent_filter_context(kwargs={'parent_id': 5})
        self.assertEqual(parent_filters, {'parent__id': 5})

        view_class = self.wrap_with_parents(child_vs, parent_vs, gp_vs)
        parent_filters = view_class.build_parent_filter_context(kwargs={
            'parent_id': 5,
            'grand_parent_id': 1
        })
        self.assertEqual(parent_filters, {'parent__grand_parent__id': 1, 'parent__id': 5})

    def test_build_parent_filter_context_missing_kwarg(self):
        child_vs = views.ChildViewSet
        parent_vs = views.ParentViewSet

        view_class = self.wrap_with_parents(child_vs, parent_vs)
        with self.assertRaises(AssertionError):
            view_class.build_parent_filter_context(kwargs={})

    def test_get_queryset_automatic_parent_filtering(self):
        grand_parent = models.GrandParent.objects.create(gp_value=100)
        parent = models.Parent.objects.create(p_value=1, grand_parent=grand_parent)
        child = models.Child.objects.create(c_value=5, parent=parent)

        other_parent = models.Parent.objects.create(p_value=2, grand_parent=grand_parent)
        models.Child.objects.create(c_value=6, parent=other_parent)

        factory = APIRequestFactory()
        view_class = self.wrap_with_parents(views.ChildViewSet, views.ParentViewSet)
        view = view_class.as_view({'get': 'list'})
        request = factory.get('/test/')
        response = self.with_request_kwargs(view, request, {'parent_id': parent.id})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['c_value'], child.c_value)

    def test_get_object(self):
        grand_parent = models.GrandParent.objects.create(gp_value=100)
        parent = models.Parent.objects.create(p_value=1, grand_parent=grand_parent)
        child = models.Child.objects.create(c_value=5, parent=parent)
        factory = APIRequestFactory()

        view_class = self.wrap_with_parents(views.ChildViewSet, views.ParentViewSet)
        view = view_class.as_view({'get': 'retrieve'})
        request = factory.get('/test/')
        response = self.with_request_kwargs(view, request, {'parent_id': parent.id, 'id': child.id})
        self.assertEqual(response.data['id'], child.id)

    def test_parent_view_for_model(self):
        view_class = self.wrap_with_parents(views.ChildViewSet, views.ParentViewSet, views.GrandParentViewSet)
        grand_parent_view = view_class.parent_view_for_model(models.GrandParent)
        self.assertTrue(issubclass(grand_parent_view, views.GrandParentViewSet))
