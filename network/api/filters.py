"""SatNOGS Network django rest framework Filters class"""
from __future__ import absolute_import

import django_filters
from django_filters.rest_framework import FilterSet

from network.base.models import Observation, Station, Transmitter


class ObservationViewFilter(FilterSet):
    """SatNOGS Network Observation API View Filter"""
    start = django_filters.IsoDateTimeFilter(name='start', lookup_expr='gte')
    end = django_filters.IsoDateTimeFilter(name='end', lookup_expr='lte')

    class Meta:
        model = Observation
        fields = [
            'id', 'ground_station', 'satellite__norad_cat_id', 'transmitter_uuid',
            'transmitter_mode', 'transmitter_type', 'vetted_status', 'vetted_user'
        ]


class StationViewFilter(FilterSet):
    """SatNOGS Network Station API View Filter"""
    class Meta:
        model = Station
        fields = ['id', 'name', 'status', 'client_version']


class TransmitterViewFilter(FilterSet):
    """SatNOGS Network Transmitter API View Filter"""
    class Meta:
        model = Transmitter
        fields = ['uuid', 'sync_to_db']
