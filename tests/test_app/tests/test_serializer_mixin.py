from unittest.mock import patch

from django.test import TestCase
from rest_framework.generics import ListAPIView
from rest_framework.test import APIRequestFactory

from drf_magic.views.mixins import AutoSerializerViewMixin
from tests.test_app.models import Person


class AutoSerializerViewMixinTestCase(TestCase):

    def test_nothing_set(self):
        factory = APIRequestFactory()
        request = factory.get('/test/')

        class TestView(AutoSerializerViewMixin, ListAPIView):

            queryset = Person.objects.all()

        view = TestView()
        with self.assertRaises(AssertionError):
            view.list(request)

    @patch('drf_magic.serializers.viewsets.load_model_serializer')
    def test_model_set(self, mocked_loader):
        expected = 1

        mocked_loader.return_value = expected

        class TestView(AutoSerializerViewMixin, ListAPIView):

            model = Person

        view = TestView()
        serializer_class = view.get_serializer_class()
        mocked_loader.assert_called_with(Person)
        self.assertEqual(expected, serializer_class)

    def test_serializer_class_set(self):
        expected = 1

        class TestView(AutoSerializerViewMixin, ListAPIView):

            serializer_class = expected

        view = TestView()
        serializer_class = view.get_serializer_class()
        self.assertEqual(expected, serializer_class)

    @patch('drf_magic.serializers.viewsets.load_model_serializer')
    def test_model_not_set(self, mocked_loader):
        mocked_loader.return_value = None

        class TestView(AutoSerializerViewMixin, ListAPIView):

            model = Person

        view = TestView()
        with self.assertRaises(AssertionError):
            view.get_serializer_class()

    def test_get_serializer_class_set(self):
        expected = 1

        class TestView(AutoSerializerViewMixin, ListAPIView):

            def get_serializer_class(self):
                return expected

        view = TestView()
        serializer_class = view.get_serializer_class()
        self.assertEqual(expected, serializer_class)

    def test_override_set(self):
        expected = 1

        class TestView(AutoSerializerViewMixin, ListAPIView):

            test_serializer_class = expected

        view = TestView()
        view.action = 'test'
        serializer_class = view.get_serializer_class()
        self.assertEqual(expected, serializer_class)
