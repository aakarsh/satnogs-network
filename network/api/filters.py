import django_filters

from network.base.models import Observation


class ObservationViewFilter(django_filters.FilterSet):
    start = django_filters.IsoDateTimeFilter(name='start', lookup_expr='gte')
    end = django_filters.IsoDateTimeFilter(name='end', lookup_expr='lte')

    class Meta:
        model = Observation
        fields = ['ground_station', 'satellite__norad_cat_id']
