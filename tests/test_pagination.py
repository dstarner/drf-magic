from django.test import TestCase
from rest_framework.decorators import action
from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import GenericViewSet

from drf_magic.pagination import PageNumberPagination, paginate
from tests.test_app import models, serializers


class PaginationTestCase(TestCase):

    def test_paginate_custom_action(self):
        count = 200
        default_per_page = 25
        people = [models.Person.objects.create(first_name='Dave', last_name=f'#{x}') for x in range(count)]

        class ShortPagination(PageNumberPagination):

            page_size = default_per_page

        class PersonViewSet(GenericViewSet):

            pagination_class = ShortPagination

            serializer_class = serializers.PersonSerializer

            @paginate
            @action(detail=False, methods=['GET'])
            def long_people_list(self, request):
                return models.Person.objects.all()

        factory = APIRequestFactory()
        request = factory.get('/test/')

        view = PersonViewSet.as_view({'get': 'long_people_list'})
        view.request = request
        response = view(request)
        self.assertEqual(response.data['count'], count)
        self.assertEqual(len(response.data['results']), default_per_page)
        for person in people:
            person.delete()
