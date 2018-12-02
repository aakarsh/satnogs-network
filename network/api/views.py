from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from rest_framework import viewsets, mixins, status
from rest_framework.response import Response

from network.api.perms import StationOwnerCanEditPermission
from network.api import serializers, filters, pagination
from network.base.models import Observation, Station, Transmitter


class ObservationView(viewsets.ModelViewSet, mixins.UpdateModelMixin):
    queryset = Observation.objects.all()
    serializer_class = serializers.ObservationSerializer
    filter_class = filters.ObservationViewFilter
    permission_classes = [
        StationOwnerCanEditPermission
    ]
    pagination_class = pagination.LinkedHeaderPageNumberPagination

    def update(self, request, *args, **kwargs):
        if request.data.get('client_version'):
            instance = self.get_object()
            instance.ground_station.client_version = request.data.get('client_version')
            instance.ground_station.save()
        if request.data.get('demoddata'):
            instance = self.get_object()
            instance.demoddata.create(payload_demod=request.data.get('demoddata'))

        super(ObservationView, self).update(request, *args, **kwargs)
        return Response(status=status.HTTP_200_OK)


class StationView(viewsets.ModelViewSet, mixins.UpdateModelMixin):
    queryset = Station.objects.all()
    serializer_class = serializers.StationSerializer
    filter_class = filters.StationViewFilter
    pagination_class = pagination.LinkedHeaderPageNumberPagination


class TransmitterView(viewsets.ModelViewSet, mixins.UpdateModelMixin):
    queryset = Transmitter.objects.all().order_by('uuid')
    serializer_class = serializers.TransmitterSerializer
    filter_class = filters.TransmitterViewFilter
    pagination_class = pagination.LinkedHeaderPageNumberPagination


class JobView(viewsets.ReadOnlyModelViewSet):
    queryset = Observation.objects.filter(payload='')
    serializer_class = serializers.JobSerializer
    filter_class = filters.ObservationViewFilter
    filter_fields = ('ground_station')

    def get_queryset(self):
        queryset = self.queryset.filter(start__gte=now())
        gs_id = self.request.query_params.get('ground_station', None)
        if gs_id and self.request.user.is_authenticated():
            gs = get_object_or_404(Station, id=gs_id)
            if gs.owner == self.request.user:
                gs.last_seen = now()
                gs.save()
        return queryset


class SettingsView(viewsets.ReadOnlyModelViewSet):
    queryset = Station.objects.all()
    lookup_field = 'uuid'

    def list(self, request):
        raise Http404()

    def retrieve(self, request, queryset=queryset, uuid=None):
        station = get_object_or_404(queryset, uuid=uuid)
        serializer = serializers.SettingsSerializer(station)
        return Response(serializer.data)
