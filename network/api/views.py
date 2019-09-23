from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from network.api import filters, pagination, serializers
from network.api.perms import StationOwnerPermission
from network.base.models import LatestTle, Observation, Station, Transmitter
from network.base.validators import NegativeElevationError, \
    ObservationOverlapError, SinglePassError


class ObservationView(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin, mixins.CreateModelMixin,
                      viewsets.GenericViewSet):
    queryset = Observation.objects.all()
    filter_class = filters.ObservationViewFilter
    permission_classes = [
        StationOwnerPermission
    ]
    pagination_class = pagination.LinkedHeaderPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.NewObservationSerializer
        return serializers.ObservationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True, allow_empty=False)
        try:
            if serializer.is_valid():
                observations = serializer.save()
                serialized_obs = serializers.ObservationSerializer(observations, many=True)
                data = serialized_obs.data
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = serializer.errors
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            data = e.message
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except LatestTle.DoesNotExist:
            data = 'Scheduling failed: Satellite without TLE'
            return Response(data, status=status.HTTP_501_NOT_IMPLEMENTED)
        except ObservationOverlapError as e:
            data = e.message
            return Response(data, status=status.HTTP_409_CONFLICT)
        except NegativeElevationError as e:
            data = e.message
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        except SinglePassError as e:
            data = e.message
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.data.get('client_version'):
            instance.ground_station.client_version = request.data.get('client_version')
            instance.ground_station.save()
        if request.data.get('demoddata'):
            try:
                file_path = 'data_obs/{0}/{1}'.format(instance.id, request.data.get('demoddata'))
                instance.demoddata.get(payload_demod=file_path)
                return Response(data='This data file has already been uploaded',
                                status=status.HTTP_403_FORBIDDEN)
            except ObjectDoesNotExist:
                instance.demoddata.create(payload_demod=request.data.get('demoddata'))
        if request.data.get('waterfall'):
            if instance.has_waterfall:
                return Response(data='Watefall has already been uploaded',
                                status=status.HTTP_403_FORBIDDEN)
        if request.data.get('payload'):
            if instance.has_audio:
                return Response(data='Audio has already been uploaded',
                                status=status.HTTP_403_FORBIDDEN)

        super(ObservationView, self).update(request, *args, **kwargs)
        return Response(status=status.HTTP_200_OK)


class StationView(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Station.objects.all()
    serializer_class = serializers.StationSerializer
    filter_class = filters.StationViewFilter
    pagination_class = pagination.LinkedHeaderPageNumberPagination


class TransmitterView(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
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
                lat = self.request.query_params.get('lat', None)
                lon = self.request.query_params.get('lon', None)
                alt = self.request.query_params.get('alt', None)
                if not (lat is None or lon is None or alt is None):
                    gs.lat = float(lat)
                    gs.lng = float(lon)
                    gs.alt = int(alt)
                gs.last_seen = now()
                gs.save()
        return queryset
