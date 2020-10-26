class _MockRouter:

    root_viewset_cls = None


class NestedRouteTestCaseMixin:

    def wrap_with_parents(self, child_class, *parent_classes):
        """
        Wraps the child_class to be a nested route below the given
        parent classes, where the last parent class is the "top route"
        """
        all_viewsets = [child_class] + list(parent_classes)
        all_viewsets.reverse()
        most_child = None

        for i, viewset in enumerate(all_viewsets):
            if i == 0:
                most_child = view_class = type(
                    f'{viewset.__name__}__TestWrapper',
                    (viewset,), dict(vars(viewset))
                )
                continue
            parent_viewset = most_child
            router = _MockRouter()
            router.root_viewset_cls = parent_viewset
            view_class = type(
                f'{viewset.__name__}__NestedTestWrapper',
                (viewset,), dict(vars(viewset))
            )
            view_class.check_parent_permissions = False
            view_class.router = router
            most_child = view_class
        return most_child

    def with_request_kwargs(self, view, request, kwargs):
        request.parser_context = {'kwargs': kwargs}
        return view(request, **request.parser_context['kwargs'])
