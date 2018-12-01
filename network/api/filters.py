import django_filters

from network.base.models import Observation, Station


class ObservationViewFilter(django_filters.FilterSet):
    start = django_filters.IsoDateTimeFilter(name='start', lookup_expr='gte')
    end = django_filters.IsoDateTimeFilter(name='end', lookup_expr='lte')

    class Meta:
        model = Observation
        fields = ['ground_station', 'satellite__norad_cat_id', 'transmitter', 'vetted_status',
                  'vetted_user', 'tle']


class StationViewFilter(django_filters.FilterSet):
    class Meta:
        model = Station
        fields = ['id', 'name', 'status', 'client_version']
