.. _serializerPage:

.. py:currentmodule:: drf_magic.serializers.loader

Model & Data Serialization
==========================

`Serializers <https://www.django-rest-framework.org/api-guide/serializers/>`_ are a
`Django Rest Framework <https://www.django-rest-framework.org/>`_ concept that describe converting
models to and from JSON, and under what circumstances. They provide a middle man that when paired
with views and viewsets can automatically parse and unparse data between requests and responses. They
provide a common interface for describing how (de)serialization works through the project and its routes.

DRF Magic provides tooling to make working with serialization even easier by including class
decorators to automatically tie serializer classes to the models that they represent. Note that
the more you buy into the different features of DRF Magic, the more powerful the automatic
serialization features become.

Model Core Serializers
----------------------

For most models, there is usually one core serializer that is used for a majority of the routes,
usually at least for **listing** of a group of instances and **retrieving** a specific instance.
This means that it may be useful to create a mapping from a model to its main serializer class, so
that instances and data of that model/request type can easily and quickly be converted back and
forth while having the serializer ⬄ model mapping declared only once, providing good *D.R.Y*
programming habits.

Registering a Main Serializer
+++++++++++++++++++++++++++++

DRF Magic has a ``register_main_serializer`` function that allows us to easily create this
serializer-to-model mapping when we define our serializers based on their defined ``Meta.model``
attributes.

.. autofunction:: register_main_serializer

We can use this in a project in the following manner. Let's say we have a ``Person`` model defined,
such as what is below.

.. code-block:: python

   from django.db import models


   class Person(models.Model):
       
       first_name = models.CharField(max_length=64, default='')
       
       last_name = models.CharField(max_length=64, default='')
       
       occupation = models.CharField(max_length=128, default='programmer')


We can then define a ``PersonalSerializer`` that is registered as the main serializer for the
above-defined ``Person`` model.

.. code-block:: python

    # my_app/serializers.py
    from drf_magic.serializers.loader import register_main_serializer
    from rest_framework import serializers

    from .models import Person

    @register_main_serializer  # <-- registers the main serializer
    class PersonSerializer(serializers.ModelSerializer):
        """Main serializer class for converting Person instances to JSON and back
        """

        class Meta:
            model = Person
            fields = ['id', 'first_name', 'last_name', 'occupation']

Notice how we include the ``@register_main_serializer`` around the serializer class definition.
That's the key feature that registers this serializer to the ``Person`` class.

We can then pull out this serializer in a declarative, but dynamic way using the
``load_model_serializer`` function.

.. autofunction:: load_model_serializer

.. code-block:: python

    # my_app/views.py
    from drf_magic.serializers.loader import load_model_serializer

    # Somewhere in our code...
    person_serializer_class = load_model_serializer(Person)
    assert person_serializer_class == PersonSerializer

Automatically Load Main Serializers
+++++++++++++++++++++++++++++++++++

Due to the nature of Django apps and how they are loaded, we must load them when the
`app configs <https://docs.djangoproject.com/en/3.1/ref/applications/#configuring-applications>`_
are ``ready()``. This can be done automatically with the ``AutoSerializerAppConfig`` class.

.. note:: 

   This does not have to be included specifically if your app configs already subclass from
   ``drf_magic.MagicAppConfig``, as this subclass is already included in that case.

.. autoclass:: AutoSerializerAppConfig

In a real example, it may look like the following, continuing with our ongoing example.

.. code-block:: python
    
    # my_app/apps.py

    # Preferred method if also using auto model accessors
    from drf_magic.apps import MagicAppConfig


    class MyAppConfig(MagicAppConfig):
        pass

    # --------------------------------

    # If needed only for serializers
    from drf_magic.serializers.loader import AutoSerializerAppConfig


    class MyAppConfig(AutoSerializerAppConfig):
        pass


Serializers in Viewsets
-----------------------

Once we have main model serializers set up for our major models, we can have :ref:`viewsets <viewsetPage>` automatically
use them when we define the viewset's ``model`` attribute. By default, DRF Magic-based viewsets
will load the main serializer for its associated views. This functionality comes from the
``AutoSerializerMixin`` viewset mixin and its overriding of ``get_serializer_class``.

.. py:currentmodule:: drf_magic.serializers.viewsets

.. autoclass:: AutoSerializerMixin

    .. automethod:: get_serializer_class(self)

With all of the following performed, we can then have model instances and data be automatically
set and converted based on the mapping of the ``Person`` model to the ``PersonSerializer`` class.

.. code-block:: python

    # my_app/views.py
    from rest_framework.responses import Response

    from .models import Person

    # TODO: Fix this import once its finalized
    class PersonViewset(AutoSerializerMixin or MagicViewset):
        """API routes to handle Person model interaction
        """
        model = Person

        # get_serializer_class() --> PersonSerializer

        # builtin actions (list, retrieve, create, delete...) will
        # expect a PersonSerializer-compatible JSON structure for
        # incoming data requests and will convert model instances
        # to the same structure on responses automatically

        @action(detail=True)
        def custom_retrieve(self, **kwargs):
            person = self.get_object()

            # This is where our main serializer setup comes into play
            serializer_class = self.get_serializer_class()

            serializer = serializer_class(instance=person)
            return Response(serializer.data)

Overridding the Main Serializer
+++++++++++++++++++++++++++++++

In some cases though, it may be deemed necessary to override what serializer to use for a
specific viewset action. This may be useful if you have custom actions on the viewset that require
different JSON data structures, or just want to have different serializers for a specific action
type.

.. tip::

    A scenario that I find myself overriding the core serializer is when implementing a generic
    main serializer for **list**-ing, and a detailed serializer when **retrieve**-ing, or vis versa.


These overrides can be implemented by placing a ``<action>_serializer_class`` attribute on the
associated viewset where ``<action>`` is the action type that the serializer class should be
overridden for.

.. code-block:: python

    from .serializers import PersonCreationSerializer


    class PersonViewset(AutoSerializerMixin or MagicViewset): 

        # used during 'create' actions
        create_class_serializer = PersonCreationSerializer

        # used during 'fire' actions
        fire_serializer = FirePersonSerializer

        @action(detail=True)
        def fire(self, **kwargs):
            serializer_class = self.get_serializer_class()
            # ... do something and return a response