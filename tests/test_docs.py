from django.test import TestCase
from rest_framework import views

from drf_magic.docs.schema import SmartSummaryAutoSchema


class MockView(views.APIView):
    pass


class TestSmartSummaryAutoSchema(TestCase):

    view = MockView.as_view()
    path = '/test'

    def __generate_auto_schema(self, method='GET'):
        return SmartSummaryAutoSchema(
            self.view, self.path, method, [], None, {}
        )

    def test_get_operation_id(self):
        arguments = ['hello', 'world', 'woo_hoo']
        expected = 'hello_world_woo_hoo'

        generator = self.__generate_auto_schema()
        actual = generator.get_operation_id(arguments)
        self.assertEqual(expected, actual)
