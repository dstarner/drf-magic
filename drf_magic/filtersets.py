from django_filters import FilterSet as DFFilterSet


class FilterSet(DFFilterSet):
    """Same as the default FilterSet, but this adds 'help_text' to fill out the API docs
    """

    @classmethod
    def filter_for_lookup(cls, field, lookup_type):
        """Overridden classmethod from django_filters.FilterSet

        We just add force the help_text field so that the API docs look nice
        """
        filter_class, params = super(FilterSet, cls).filter_for_lookup(field, lookup_type)
        params['help_text'] = field.help_text
        return filter_class, params
