"""SatNOGS Network django rest framework Filters class"""
import django_filters
from django.utils.timezone import now
from django_filters.rest_framework import FilterSet

from network.base.models import Observation, Station
from network.users.models import User


class ObservationViewFilter(FilterSet):
    """SatNOGS Network Observation API View Filter"""
    OBSERVATION_STATUS_CHOICES = [
        ('failed', 'Failed'),
        ('bad', 'Bad'),
        ('unknown', 'Unknown'),
        ('future', 'Future'),
        ('good', 'Good'),
    ]

    WATERFALL_STATUS_CHOICES = [
        (1, 'With Signal'),
        (0, 'Without Signal'),
    ]

    # DEPRECATED
    VETTED_STATUS_CHOICES = [
        ('failed', 'Failed'),
        ('bad', 'Bad'),
        ('unknown', 'Unknown'),
        ('good', 'Good'),
    ]

    start = django_filters.IsoDateTimeFilter(field_name='start', lookup_expr='gte')
    end = django_filters.IsoDateTimeFilter(field_name='end', lookup_expr='lte')
    status = django_filters.ChoiceFilter(
        field_name='status', choices=OBSERVATION_STATUS_CHOICES, method='filter_status'
    )
    waterfall_status = django_filters.ChoiceFilter(
        field_name='waterfall_status', choices=WATERFALL_STATUS_CHOICES, null_label='Unknown'
    )
    vetted_status = django_filters.ChoiceFilter(
        label='Vetted status (deprecated: please use Status)',
        field_name='status',
        choices=VETTED_STATUS_CHOICES,
        method='filter_status'
    )
    vetted_user = django_filters.ModelChoiceFilter(
        label='Vetted user (deprecated: will be removed in next version)',
        field_name='waterfall_status_user',
        queryset=User.objects.all()
    )

    # see https://django-filter.readthedocs.io/en/master/ref/filters.html for W0613
    def filter_status(self, queryset, name, value):  # pylint: disable=W0613,R0201
        """ Returns filtered observations for a given observation status"""
        if value == 'failed':
            observations = queryset.filter(status__lt=-100)
        if value == 'bad':
            observations = queryset.filter(status__range=(-100, -1))
        if value == 'unknown':
            observations = queryset.filter(status__range=(0, 99), end__lte=now())
        if value == 'future':
            observations = queryset.filter(end__gt=now())
        if value == 'good':
            observations = queryset.filter(status__gte=100)
        return observations

    class Meta:
        model = Observation
        fields = [
            'id', 'status', 'ground_station', 'start', 'end', 'satellite__norad_cat_id',
            'transmitter_uuid', 'transmitter_mode', 'transmitter_type', 'waterfall_status',
            'vetted_status', 'vetted_user'
        ]


class StationViewFilter(FilterSet):
    """SatNOGS Network Station API View Filter"""
    class Meta:
        model = Station
        fields = ['id', 'name', 'status', 'client_version']


class TransmitterViewFilter(FilterSet):
    """SatNOGS Network Transmitter API View Filter"""
    uuid = django_filters.CharFilter(field_name='transmitter_uuid')
