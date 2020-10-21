from django.test import TestCase

from drf_magic.utils import dict_to_filter_params


class FlattenFilterDictTestCase(TestCase):

    def test_flatten_filter_dict(self):
        nested = {
            'name': 'hello',
            'tenant': {
                'id': 5
            }
        }
        expected = {'name': 'hello', 'tenant__id': 5}
        self.assertEqual(dict_to_filter_params(nested), expected)
