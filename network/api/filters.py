from django_filters.rest_framework import FilterSet
import django_filters

from network.base.models import Observation, Station, Transmitter


class ObservationViewFilter(FilterSet):
    start = django_filters.IsoDateTimeFilter(name='start', lookup_expr='gte')
    end = django_filters.IsoDateTimeFilter(name='end', lookup_expr='lte')

    class Meta:
        model = Observation
        fields = ['id', 'ground_station', 'satellite__norad_cat_id', 'transmitter_uuid',
                  'transmitter_mode', 'transmitter_type', 'vetted_status', 'vetted_user']


class StationViewFilter(FilterSet):
    class Meta:
        model = Station
        fields = ['id', 'name', 'status', 'client_version']


class TransmitterViewFilter(FilterSet):
    class Meta:
        model = Transmitter
        fields = ['uuid', 'sync_to_db']
