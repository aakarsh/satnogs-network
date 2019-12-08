"""Django base views for SatNOGS Network"""
from __future__ import absolute_import

from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter

import ephem
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Count, Prefetch
from django.forms import ValidationError, formset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import make_aware, now, utc
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from rest_framework import serializers, viewsets

from network.base.db_api import DBConnectionError, get_transmitter_by_uuid, \
    get_transmitters_by_norad_id, get_transmitters_by_status
from network.base.decorators import admin_required, ajax_required
from network.base.forms import BaseObservationFormSet, ObservationForm, \
    SatelliteFilterForm, StationForm
from network.base.models import Antenna, LatestTle, Observation, Satellite, \
    Station, StationStatusLog
from network.base.perms import delete_perms, schedule_perms, \
    schedule_station_perms, vet_perms
from network.base.scheduling import create_new_observation, \
    get_available_stations, predict_available_observation_windows
from network.base.stats import satellite_stats_by_transmitter_list, \
    transmitter_stats_by_uuid
from network.base.tasks import fetch_data, update_all_tle
from network.base.utils import community_get_discussion_details
from network.base.validators import NegativeElevationError, \
    ObservationOverlapError, SinglePassError, \
    is_transmitter_in_station_range
from network.users.models import User


class StationSerializer(serializers.ModelSerializer):
    """Django model Serializer for Station model"""
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = ('name', 'lat', 'lng', 'id', 'status', 'status_display')

    def get_status_display(self, obj):  # pylint: disable=no-self-use
        """Returns the station status"""
        try:
            return obj.get_status_display()
        except AttributeError:
            return None


class StationAllView(viewsets.ReadOnlyModelViewSet):  # pylint: disable=R0901
    """Station View of all non offline stations"""
    queryset = Station.objects.exclude(status=0)
    serializer_class = StationSerializer


def index(request):
    """View to render index page."""
    return render(
        request, 'base/home.html', {
            'mapbox_id': settings.MAPBOX_MAP_ID,
            'mapbox_token': settings.MAPBOX_TOKEN
        }
    )


def robots(request):
    """Returns response for robots.txt requests"""
    data = render(request, 'robots.txt', {'environment': settings.ENVIRONMENT})
    response = HttpResponse(data, content_type='text/plain; charset=utf-8')
    return response


@admin_required
def settings_site(request):
    """View to render settings page."""
    if request.method == 'POST':
        fetch_data.delay()
        update_all_tle.delay()
        messages.success(request, 'Data fetching task was triggered successfully!')
        return redirect(reverse('users:view_user', kwargs={"username": request.user.username}))
    return render(request, 'base/settings_site.html')


class ObservationListView(ListView):  # pylint: disable=R0901
    """
    Displays a list of observations with pagination
    """
    model = Observation
    context_object_name = "observations"
    paginate_by = settings.ITEMS_PER_PAGE
    template_name = 'base/observations.html'
    str_filters = ['norad', 'observer', 'station', 'start', 'end']
    flag_filters = ['bad', 'good', 'unvetted', 'future', 'failed']

    def get_filter_params(self):
        """
        Get the parsed filter parameters from the HTTP GET parameters

        - str_filters vaues are str, default to ''
        - flag_filters values are Boolean, default to False

        Returns a dict, filter_name is the key, the parsed parameter is the value.
        """
        filter_params = {}
        for parameter_name in self.str_filters:
            filter_params[parameter_name] = self.request.GET.get(parameter_name, '')

        for parameter_name in self.flag_filters:
            param = self.request.GET.get(parameter_name, 1)
            filter_params[parameter_name] = (param != '0')

        return filter_params

    def get_queryset(self):
        """
        Optionally filter based on norad get argument
        Optionally filter based on future/good/bad/unvetted/failed
        """
        filter_params = self.get_filter_params()

        results = self.request.GET.getlist('results')

        observations = Observation.objects.prefetch_related(
            'satellite', 'demoddata', 'author', 'ground_station'
        )

        # Mapping between the HTTP POST parameters and the fiter keys
        parameter_filter_mapping = {
            'norad': 'satellite__norad_cat_id',
            'observer': 'author',
            'station': 'ground_station_id',
            'start': 'start__gt',
            'end': 'end__lt',
        }

        # Create observations filter based on the received HTTP POST parameters
        filter_dict = {}
        for parameter_key, filter_key in parameter_filter_mapping.items():
            if filter_params[parameter_key] == '':
                continue

            filter_dict[filter_key] = filter_params[parameter_key]

        self.filtered = (
            (
                not all(
                    [
                        filter_params['bad'], filter_params['good'], filter_params['unvetted'],
                        filter_params['future'], filter_params['failed']
                    ]
                )
            ) or results or filter_dict
        )

        observations = observations.filter(**filter_dict)

        for filter_name in ['bad', 'good', 'failed']:
            if not filter_params[filter_name]:
                observations = observations.exclude(vetted_status=filter_name)

        if not filter_params['unvetted']:
            observations = observations.exclude(vetted_status='unknown', end__lte=now())
        if not filter_params['future']:
            observations = observations.exclude(vetted_status='unknown', end__gt=now())
        if results:
            if 'w0' in results:
                observations = observations.filter(waterfall='')
            elif 'w1' in results:
                observations = observations.exclude(waterfall='')
            if 'a0' in results:
                observations = observations.exclude(archived=True).filter(payload='')
            elif 'a1' in results:
                observations = observations.exclude(archived=False, payload='')
            if 'd0' in results:
                observations = observations.filter(demoddata__payload_demod__isnull=True)
            elif 'd1' in results:
                observations = observations.exclude(demoddata__payload_demod__isnull=True)
        return observations

    def get_context_data(self, **kwargs):
        """
        Need to add a list of satellites to the context for the template
        """
        # NOTE: Remove the following pylint disable after Python 3 migration
        #       (false positive due to .order_by in the following lines)
        # pylint: disable=E1101
        context = super(ObservationListView, self).get_context_data(**kwargs)
        context['satellites'] = Satellite.objects.all()
        observers_ids = list(set(Observation.objects.values_list('author_id', flat=True)))
        context['authors'] = User.objects.filter(id__in=observers_ids) \
                                         .order_by('first_name', 'last_name', 'username')
        context['stations'] = Station.objects.all().order_by('id')
        norad_cat_id = self.request.GET.get('norad', None)
        observer = self.request.GET.get('observer', None)
        station = self.request.GET.get('station', None)
        start = self.request.GET.get('start', None)
        end = self.request.GET.get('end', None)
        context['future'] = self.request.GET.get('future', '1')
        context['bad'] = self.request.GET.get('bad', '1')
        context['good'] = self.request.GET.get('good', '1')
        context['unvetted'] = self.request.GET.get('unvetted', '1')
        context['failed'] = self.request.GET.get('failed', '1')
        context['results'] = self.request.GET.getlist('results')
        context['filtered'] = self.filtered
        if norad_cat_id is not None and norad_cat_id != '':
            context['norad'] = int(norad_cat_id)
        if observer is not None and observer != '':
            context['observer_id'] = int(observer)
        if station is not None and station != '':
            context['station_id'] = int(station)
        if start is not None and start != '':
            context['start'] = start
        if end is not None and end != '':
            context['end'] = end
        if 'scheduled' in self.request.session:
            context['scheduled'] = self.request.session['scheduled']
            try:
                del self.request.session['scheduled']
            except KeyError:
                pass
        context['can_schedule'] = schedule_perms(self.request.user)
        return context


def create_new_observations(formset, user):
    """Creates new observations from formset. Error handling is performed by upper layers."""
    new_observations = []
    for observation_data in formset.cleaned_data:
        transmitter_uuid = observation_data['transmitter_uuid']
        transmitter = formset.transmitters[transmitter_uuid]

        observation = create_new_observation(
            station=observation_data['ground_station'],
            transmitter=transmitter,
            start=observation_data['start'],
            end=observation_data['end'],
            author=user
        )
        new_observations.append(observation)

    for observation in new_observations:
        observation.save()

    return new_observations


def observation_new_post(request):
    """Handles POST requests for creating one or more new observations."""
    ObservationFormSet = formset_factory(  # pylint: disable=C0103
        ObservationForm, formset=BaseObservationFormSet, min_num=1, validate_min=True
    )
    formset = ObservationFormSet(request.user, request.POST, prefix='obs')
    try:
        if not formset.is_valid():
            errors_list = [error for error in formset.errors if error]
            if errors_list:
                for field in errors_list[0]:
                    messages.error(request, '{0}'.format(errors_list[0][field][0]))
            else:
                messages.error(request, '{0}'.format(formset.non_form_errors()[0]))
            return redirect(reverse('base:observation_new'))

        new_observations = create_new_observations(formset, request.user)

        if 'scheduled' in request.session:
            del request.session['scheduled']
        request.session['scheduled'] = list(obs.id for obs in new_observations)

        # If it's a single observation redirect to that one
        total = formset.total_form_count()
        if total == 1:
            messages.success(request, 'Observation was scheduled successfully.')
            response = redirect(
                reverse(
                    'base:observation_view', kwargs={'observation_id': new_observations[0].id}
                )
            )
        else:
            messages.success(request, str(total) + ' Observations were scheduled successfully.')
            response = redirect(reverse('base:observations_list'))
    except (ValueError, ValidationError, ObservationOverlapError, NegativeElevationError,
            SinglePassError) as error:
        messages.error(request, '{0}'.format(error.message))
        response = redirect(reverse('base:observation_new'))
    except LatestTle.DoesNotExist:
        message = 'Scheduling failed: Satellite without TLE'
        messages.error(request, '{0}'.format(message))
        response = redirect(reverse('base:observation_new'))
    return response


@login_required
def observation_new(request):
    """View for new observation"""
    can_schedule = schedule_perms(request.user)
    if not can_schedule:
        messages.error(request, 'You don\'t have permissions to schedule observations')
        return redirect(reverse('base:observations_list'))

    if request.method == 'POST':
        return observation_new_post(request)

    satellites = Satellite.objects.filter(status='alive')

    obs_filter = {}
    if request.method == 'GET':
        filter_form = SatelliteFilterForm(request.GET)
        if filter_form.is_valid():
            start = filter_form.cleaned_data['start']
            end = filter_form.cleaned_data['end']
            ground_station = filter_form.cleaned_data['ground_station']
            transmitter = filter_form.cleaned_data['transmitter']
            norad = filter_form.cleaned_data['norad']

            obs_filter['dates'] = False
            if start and end:  # Either give both dates or ignore if only one is given
                start = datetime.strptime(start, '%Y/%m/%d %H:%M').strftime('%Y-%m-%d %H:%M')
                end = (datetime.strptime(end, '%Y/%m/%d %H:%M') +
                       timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M')
                obs_filter['start'] = start
                obs_filter['end'] = end
                obs_filter['dates'] = True

            obs_filter['exists'] = True
            if norad:
                obs_filter['norad'] = norad
                obs_filter['transmitter'] = transmitter  # Add transmitter only if norad exists
            if ground_station:
                obs_filter['ground_station'] = ground_station
        else:
            obs_filter['exists'] = False

    return render(
        request, 'base/observation_new.html', {
            'satellites': satellites,
            'obs_filter': obs_filter,
            'date_min_start': settings.OBSERVATION_DATE_MIN_START,
            'date_min_end': settings.OBSERVATION_DATE_MIN_END,
            'date_max_range': settings.OBSERVATION_DATE_MAX_RANGE,
            'warn_min_obs': settings.OBSERVATION_WARN_MIN_OBS
        }
    )


def prediction_windows_parse_parameters(request):
    """ Parse HTTP parameters with defaults"""
    return {
        'sat_norad_id': request.POST['satellite'],
        'transmitter': request.POST['transmitter'],
        'start': make_aware(datetime.strptime(request.POST['start'], '%Y-%m-%d %H:%M'), utc),
        'end': make_aware(datetime.strptime(request.POST['end'], '%Y-%m-%d %H:%M'), utc),
        'station_ids': request.POST.getlist('stations[]', []),
        'min_horizon': request.POST.get('min_horizon', None),
        'overlapped': int(request.POST.get('overlapped', 0)),
    }


@ajax_required
def prediction_windows(request):
    """Calculates and returns passes of satellites over stations"""

    params = prediction_windows_parse_parameters(request)

    # Check the selected satellite exists and is alive
    try:
        sat = Satellite.objects.filter(status='alive').get(norad_cat_id=params['sat_norad_id'])
    except Satellite.DoesNotExist:
        data = [{'error': 'You should select a Satellite first.'}]
        return JsonResponse(data, safe=False)

    # Check there is a TLE available for this satellite
    try:
        tle = LatestTle.objects.get(satellite_id=sat.id)
    except LatestTle.DoesNotExist:
        data = [{'error': 'No TLEs for this satellite yet.'}]
        return JsonResponse(data, safe=False)

    # Check the selected transmitter exists, and if yes,
    # store this transmitter in the downlink variable
    try:
        transmitter = get_transmitter_by_uuid(params['transmitter'])
        if not transmitter:
            data = [{'error': 'You should select a valid Transmitter.'}]
            return JsonResponse(data, safe=False)
        downlink = transmitter[0]['downlink_low']
    except DBConnectionError as error:
        data = [{'error': error.message}]
        return JsonResponse(data, safe=False)

    # Fetch all available ground stations
    stations = Station.objects.filter(status__gt=0).prefetch_related(
        Prefetch(
            'observations',
            queryset=Observation.objects.filter(end__gt=now()),
            to_attr='scheduled_obs'
        ), 'antenna'
    )

    if params['station_ids'] and params['station_ids'] != ['']:
        # Filter ground stations based on the given selection
        stations = stations.filter(id__in=params['station_ids'])
        if not stations:
            if len(params['station_ids']) == 1:
                data = [{'error': 'Station is offline or it doesn\'t exist.'}]
            else:
                data = [{'error': 'Stations are offline or they don\'t exist.'}]
            return JsonResponse(data, safe=False)

    available_stations = get_available_stations(stations, downlink, request.user)

    data = []
    passes_found = defaultdict(list)
    for station in available_stations:
        station_passes, station_windows = predict_available_observation_windows(
            station, params['min_horizon'], params['overlapped'], tle, params['start'],
            params['end']
        )
        passes_found[station.id] = station_passes
        if station_windows:
            data.append(
                {
                    'id': station.id,
                    'name': station.name,
                    'status': station.status,
                    'lng': station.lng,
                    'lat': station.lat,
                    'alt': station.alt,
                    'window': station_windows
                }
            )

    if not data:
        error_message = 'Satellite is always below horizon or ' \
                        'no free observation time available on visible stations.'
        error_details = {}
        for station in available_stations:
            if station.id not in passes_found:
                error_details[station.id] = 'Satellite is always above or below horizon.\n'
            else:
                error_details[station.id] = 'No free observation time during passes available.\n'

        data = [
            {
                'error': error_message,
                'error_details': error_details,
                'passes_found': passes_found
            }
        ]

    return JsonResponse(data, safe=False)


def observation_view(request, observation_id):
    """View for single observation page."""
    observation = get_object_or_404(Observation, id=observation_id)

    can_vet = vet_perms(request.user, observation)

    can_delete = delete_perms(request.user, observation)

    if observation.has_audio and not observation.audio_url:
        messages.error(
            request, 'Audio file is not currently available,'
            ' if the problem persists please contact an administrator.'
        )

    if settings.ENVIRONMENT == 'production':
        discussion_details = community_get_discussion_details(
            observation.id, observation.satellite.name, observation.satellite.norad_cat_id,
            'http://{}{}'.format(request.get_host(), request.path)
        )

        return render(
            request, 'base/observation_view.html', {
                'observation': observation,
                'has_comments': discussion_details['has_comments'],
                'discuss_url': discussion_details['url'],
                'discuss_slug': discussion_details['slug'],
                'can_vet': can_vet,
                'can_delete': can_delete
            }
        )

    return render(
        request, 'base/observation_view.html', {
            'observation': observation,
            'can_vet': can_vet,
            'can_delete': can_delete
        }
    )


@login_required
def observation_delete(request, observation_id):
    """View for deleting observation."""
    observation = get_object_or_404(Observation, id=observation_id)
    can_delete = delete_perms(request.user, observation)
    if can_delete:
        observation.delete()
        messages.success(request, 'Observation deleted successfully.')
    else:
        messages.error(request, 'Permission denied.')
    return redirect(reverse('base:observations_list'))


@login_required
@ajax_required
def observation_vet(request, observation_id):
    """Handles request for vetting an observation"""
    try:
        observation = Observation.objects.get(id=observation_id)
    except Observation.DoesNotExist:
        data = {'error': 'Observation does not exist.'}
        return JsonResponse(data, safe=False)

    status = request.POST.get('status', None)
    can_vet = vet_perms(request.user, observation)

    if status not in ['good', 'bad', 'failed', 'unknown']:
        data = {
            'error': 'Invalid status, select one of \'good\', \'bad\', \'failed\' and \'unknown\'.'
        }
        return JsonResponse(data, safe=False)
    if not can_vet:
        data = {'error': 'Permission denied.'}
        return JsonResponse(data, safe=False)

    observation.vetted_status = status
    observation.vetted_user = request.user
    observation.vetted_datetime = now()
    observation.save(update_fields=['vetted_status', 'vetted_user', 'vetted_datetime'])
    data = {
        'vetted_status': observation.vetted_status,
        'vetted_status_display': observation.get_vetted_status_display(),
        'vetted_user': observation.vetted_user.displayname,
        'vetted_datetime': observation.vetted_datetime.strftime('%Y-%m-%d %H:%M:%S')
    }
    return JsonResponse(data, safe=False)


def stations_list(request):
    """View to render Stations page."""
    stations = Station.objects.prefetch_related(
        'antenna', 'owner',
        Prefetch(
            'observations',
            queryset=Observation.objects.filter(end__gt=now()),
            to_attr='scheduled_obs'
        )
    ).order_by('-status', 'id')
    stations_total_obs = {
        x['id']: x['total_obs']
        for x in Station.objects.values('id').annotate(total_obs=Count('observations'))
    }
    antennas = Antenna.objects.all()
    stations_by_status = {'online': 0, 'testing': 0, 'offline': 0, 'future': 0}
    for station in stations:
        if station.last_seen is None:
            stations_by_status['future'] += 1
        elif station.status == 2:
            stations_by_status['online'] += 1
        elif station.status == 1:
            stations_by_status['testing'] += 1
        else:
            stations_by_status['offline'] += 1

    return render(
        request, 'base/stations.html', {
            'stations': stations,
            'total_obs': stations_total_obs,
            'antennas': antennas,
            'online': stations_by_status['online'],
            'testing': stations_by_status['testing'],
            'offline': stations_by_status['offline'],
            'future': stations_by_status['future'],
            'mapbox_id': settings.MAPBOX_MAP_ID,
            'mapbox_token': settings.MAPBOX_TOKEN
        }
    )


def station_view(request, station_id):
    """View for single station page."""
    station = get_object_or_404(Station, id=station_id)
    form = StationForm(instance=station)
    antennas = Antenna.objects.all()
    unsupported_frequencies = request.GET.get('unsupported_frequencies', '0')

    can_schedule = schedule_station_perms(request.user, station)

    # Calculate uptime
    uptime = '-'
    try:
        latest = StationStatusLog.objects.filter(station=station)[0]
    except IndexError:
        latest = None
    if latest:
        if latest.status:
            try:
                offline = StationStatusLog.objects.filter(station=station, status=0)[0]
                uptime = latest.changed - offline.changed
            except IndexError:
                uptime = now() - latest.changed
            uptime = str(uptime).split('.')[0]

    if request.user.is_authenticated():
        if request.user == station.owner:
            wiki_help = (
                '<a href="{0}" target="_blank" class="wiki-help"><span class="glyphicon '
                'glyphicon-question-sign" aria-hidden="true"></span>'
                '</a>'.format(settings.WIKI_STATION_URL)
            )
            if station.is_offline:
                messages.error(
                    request, (
                        'Your Station is offline. You should make '
                        'sure it can successfully connect to the Network API. '
                        '{0}'.format(wiki_help)
                    )
                )
            if station.is_testing:
                messages.warning(
                    request, (
                        'Your Station is in Testing mode. Once you are sure '
                        'it returns good observations you can put it online. '
                        '{0}'.format(wiki_help)
                    )
                )

    return render(
        request, 'base/station_view.html', {
            'station': station,
            'form': form,
            'antennas': antennas,
            'mapbox_id': settings.MAPBOX_MAP_ID,
            'mapbox_token': settings.MAPBOX_TOKEN,
            'can_schedule': can_schedule,
            'unsupported_frequencies': unsupported_frequencies,
            'uptime': uptime
        }
    )


def station_log_view(request, station_id):
    """View for single station status log."""
    station = get_object_or_404(Station, id=station_id)
    station_log = StationStatusLog.objects.filter(station=station)

    return render(
        request, 'base/station_log.html', {
            'station': station,
            'station_log': station_log
        }
    )


@ajax_required
def scheduling_stations(request):
    """Returns json with stations on which user has permissions to schedule"""
    uuid = request.POST.get('transmitter', None)
    if uuid is None:
        data = [{'error': 'You should select a Transmitter.'}]
        return JsonResponse(data, safe=False)
    try:
        transmitter = get_transmitter_by_uuid(uuid)
        if not transmitter:
            data = [{'error': 'You should select a valid Transmitter.'}]
            return JsonResponse(data, safe=False)
        downlink = transmitter[0]['downlink_low']
        if downlink is None:
            data = [{'error': 'You should select a valid Transmitter.'}]
            return JsonResponse(data, safe=False)
    except DBConnectionError as error:
        data = [{'error': error.message}]
        return JsonResponse(data, safe=False)

    stations = Station.objects.filter(status__gt=0).prefetch_related('antenna')
    available_stations = get_available_stations(stations, downlink, request.user)
    data = {
        'stations': StationSerializer(available_stations, many=True).data,
    }
    return JsonResponse(data, safe=False)


@ajax_required
def pass_predictions(request, station_id):
    """Endpoint for pass predictions"""
    station = get_object_or_404(
        Station.objects.prefetch_related(
            Prefetch(
                'observations',
                queryset=Observation.objects.filter(end__gt=now()),
                to_attr='scheduled_obs'
            ), 'antenna'
        ),
        id=station_id
    )
    unsupported_frequencies = request.GET.get('unsupported_frequencies', '0')

    try:
        latest_tle_queryset = LatestTle.objects.all()
        satellites = Satellite.objects.filter(status='alive').prefetch_related(
            Prefetch('tles', queryset=latest_tle_queryset, to_attr='tle')
        )
    except Satellite.DoesNotExist:
        pass  # we won't have any next passes to display

    # Load the station information and invoke ephem so we can
    # calculate upcoming passes for the station
    observer = ephem.Observer()
    observer.lon = str(station.lng)
    observer.lat = str(station.lat)
    observer.elevation = station.alt
    observer.horizon = str(station.horizon)

    nextpasses = []
    start = make_aware(datetime.utcnow(), utc)
    end = make_aware(datetime.utcnow() + timedelta(hours=settings.STATION_UPCOMING_END), utc)
    observation_min_start = (
        datetime.utcnow() + timedelta(minutes=settings.OBSERVATION_DATE_MIN_START)
    ).strftime("%Y-%m-%d %H:%M:%S.%f")

    try:
        all_transmitters = get_transmitters_by_status('active')
    except DBConnectionError:
        all_transmitters = []

    if all_transmitters:
        for satellite in satellites:
            # look for a match between transmitters from the satellite and
            # ground station antenna frequency capabilities
            if int(unsupported_frequencies) == 0:
                norad_id = satellite.norad_cat_id
                transmitters = [
                    t for t in all_transmitters if t['norad_cat_id'] == norad_id
                    and is_transmitter_in_station_range(t, station)  # noqa: W503
                ]
                if not transmitters:
                    continue

            if satellite.tle:
                tle = satellite.tle[0]
            else:
                continue

            _, station_windows = predict_available_observation_windows(
                station, None, 2, tle, start, end
            )

            if station_windows:
                satellite_stats = satellite_stats_by_transmitter_list(transmitters)
                for window in station_windows:
                    valid = window['start'] > observation_min_start and window['valid_duration']
                    window_start = datetime.strptime(window['start'], '%Y-%m-%d %H:%M:%S.%f')
                    window_end = datetime.strptime(window['end'], '%Y-%m-%d %H:%M:%S.%f')
                    sat_pass = {
                        'name': str(satellite.name),
                        'id': str(satellite.id),
                        'success_rate': str(satellite_stats['success_rate']),
                        'bad_rate': str(satellite_stats['bad_rate']),
                        'unvetted_rate': str(satellite_stats['unvetted_rate']),
                        'future_rate': str(satellite_stats['future_rate']),
                        'total_count': str(satellite_stats['total_count']),
                        'good_count': str(satellite_stats['good_count']),
                        'bad_count': str(satellite_stats['bad_count']),
                        'unvetted_count': str(satellite_stats['unvetted_count']),
                        'future_count': str(satellite_stats['future_count']),
                        'norad_cat_id': str(satellite.norad_cat_id),
                        'tle1': window['tle1'],
                        'tle2': window['tle2'],
                        'tr': window_start,  # Rise time
                        'azr': window['az_start'],  # Rise Azimuth
                        'altt': window['elev_max'],  # Max altitude
                        'ts': window_end,  # Set time
                        'azs': window['az_end'],  # Set azimuth
                        'valid': valid,
                        'overlapped': window['overlapped'],
                        'overlap_ratio': window['overlap_ratio']
                    }
                    nextpasses.append(sat_pass)

    data = {
        'id': station_id,
        'nextpasses': sorted(nextpasses, key=itemgetter('tr')),
        'ground_station': {
            'lng': str(station.lng),
            'lat': str(station.lat),
            'alt': station.alt
        }
    }

    return JsonResponse(data, safe=False)


def station_edit(request, station_id=None):
    """Edit or add a single station."""
    station = None
    antennas = Antenna.objects.all()
    if station_id:
        station = get_object_or_404(Station, id=station_id, owner=request.user)

    if request.method == 'POST':
        if station:
            form = StationForm(request.POST, request.FILES, instance=station)
        else:
            form = StationForm(request.POST, request.FILES)
        if form.is_valid():
            station_form = form.save(commit=False)
            if not station:
                station_form.testing = True
            station_form.owner = request.user
            station_form.save()
            form.save_m2m()
            messages.success(request, 'Ground Station saved successfully.')
            return redirect(reverse('base:station_view', kwargs={'station_id': station_form.id}))
        messages.error(
            request, ('Your Ground Station submission has some '
                      'errors. {0}').format(form.errors)
        )
        return render(
            request, 'base/station_edit.html', {
                'form': form,
                'station': station,
                'antennas': antennas
            }
        )
    if station:
        form = StationForm(instance=station)
    else:
        form = StationForm()
    return render(
        request, 'base/station_edit.html', {
            'form': form,
            'station': station,
            'antennas': antennas
        }
    )


@login_required
def station_delete(request, station_id):
    """View for deleting a station."""
    username = request.user
    station = get_object_or_404(Station, id=station_id, owner=request.user)
    station.delete()
    messages.success(request, 'Ground Station deleted successfully.')
    return redirect(reverse('users:view_user', kwargs={'username': username}))


def transmitters_with_stats(transmitters_list):
    """Returns a list of transmitters with their statistics"""
    transmitters_with_stats_list = []
    for transmitter in transmitters_list:
        transmitter_stats = transmitter_stats_by_uuid(transmitter['uuid'])
        transmitter_with_stats = dict(transmitter, **transmitter_stats)
        transmitters_with_stats_list.append(transmitter_with_stats)
    return transmitters_with_stats_list


def satellite_view(request, norad_id):
    """Returns a satellite JSON object with information and statistics"""
    try:
        sat = Satellite.objects.get(norad_cat_id=norad_id)
    except Satellite.DoesNotExist:
        data = {'error': 'Unable to find that satellite.'}
        return JsonResponse(data, safe=False)

    try:
        transmitters = get_transmitters_by_norad_id(norad_id=norad_id)
    except DBConnectionError as error:
        data = [{'error': error.message}]
        return JsonResponse(data, safe=False)
    satellite_stats = satellite_stats_by_transmitter_list(transmitters)
    data = {
        'id': norad_id,
        'name': sat.name,
        'names': sat.names,
        'image': sat.image,
        'success_rate': satellite_stats['success_rate'],
        'good_count': satellite_stats['good_count'],
        'bad_count': satellite_stats['bad_count'],
        'unvetted_count': satellite_stats['unvetted_count'],
        'future_count': satellite_stats['future_count'],
        'total_count': satellite_stats['total_count'],
        'transmitters': transmitters_with_stats(transmitters)
    }

    return JsonResponse(data, safe=False)


@require_POST
def transmitters_view(request):
    """Returns a transmitter JSON object with information and statistics"""
    norad_id = request.POST['satellite']
    station_id = request.POST.get('station_id', None)
    try:
        Satellite.objects.get(norad_cat_id=norad_id)
    except Satellite.DoesNotExist:
        data = {'error': 'Unable to find that satellite.'}
        return JsonResponse(data, safe=False)

    try:
        transmitters = get_transmitters_by_norad_id(norad_id)
    except DBConnectionError as error:
        data = [{'error': error.message}]
        return JsonResponse(data, safe=False)

    transmitters = [
        t for t in transmitters if t['status'] == 'active' and t['downlink_low'] is not None
    ]
    if station_id:
        supported_transmitters = []
        station = Station.objects.get(id=station_id)
        for transmitter in transmitters:
            transmitter_supported = is_transmitter_in_station_range(transmitter, station)
            if transmitter_supported:
                supported_transmitters.append(transmitter)
        transmitters = supported_transmitters

    data = {'transmitters': transmitters_with_stats(transmitters)}

    return JsonResponse(data, safe=False)
