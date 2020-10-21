from rest_framework_nested import routers


class SimpleRouter(routers.SimpleRouter):
    """A little secret sauce that adds the router attribute onto the viewset if possible
    """

    def __init__(self, *args, name='root', **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)

    def register(self, prefix, viewset, *args, **kwargs):
        viewset.router = self
        return super().register(prefix, viewset, *args, **kwargs)

    def get_default_basename(self, viewset):
        return viewset.get_base_name()


class NestedRouter(routers.NestedSimpleRouter):
    """A little secret sauce that adds the router attribute onto the viewset if possible
    """
    def __init__(self, *args, name='nested', root_viewset_cls=None, **kwargs):
        self.name = name
        self.root_viewset_cls = root_viewset_cls
        try:
            super().__init__(*args, **kwargs)
        except RuntimeError:
            raise ValueError(self.root_viewset_cls)

    def register(self, prefix, viewset, *args, **kwargs):
        return super().register(prefix, viewset, *args, **kwargs)

    def get_default_basename(self, viewset):
        return viewset.get_base_name()
