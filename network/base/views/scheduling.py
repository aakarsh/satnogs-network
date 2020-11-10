"""Django base views for SatNOGS Network"""
from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import make_aware, now, utc
from django.views.decorators.http import require_POST

from network.base.db_api import DBConnectionError, get_tle_set_by_norad_id, get_tle_sets, \
    get_transmitter_by_uuid, get_transmitters_by_norad_id, get_transmitters_by_status
from network.base.decorators import ajax_required
from network.base.forms import ObservationFormSet, SatelliteFilterForm
from network.base.models import Observation, Satellite, Station
from network.base.perms import schedule_perms
from network.base.scheduling import create_new_observation, get_available_stations, \
    predict_available_observation_windows
from network.base.serializers import StationSerializer
from network.base.stats import satellite_stats_by_transmitter_list, transmitters_with_stats
from network.base.validators import NegativeElevationError, NoTleSetError, \
    ObservationOverlapError, SinglePassError, is_transmitter_in_station_range


def create_new_observations(formset, user):
    """Creates new observations from formset. Error handling is performed by upper layers."""
    new_observations = []
    for observation_data in formset.cleaned_data:
        transmitter_uuid = observation_data['transmitter_uuid']
        transmitter = formset.transmitters[transmitter_uuid]
        tle_set = formset.tle_sets[transmitter['norad_cat_id']]

        observation = create_new_observation(
            station=observation_data['ground_station'],
            transmitter=transmitter,
            start=observation_data['start'],
            end=observation_data['end'],
            author=user,
            tle_set=tle_set,
        )
        new_observations.append(observation)

    for observation in new_observations:
        observation.save()

    return new_observations


def observation_new_post(request):
    """Handles POST requests for creating one or more new observations."""
    formset = ObservationFormSet(request.user, request.POST, prefix='obs')
    try:
        if not formset.is_valid():
            errors_list = [error for error in formset.errors if error]
            if errors_list:
                for field in errors_list[0]:
                    messages.error(request, str(errors_list[0][field][0]))
            else:
                messages.error(request, str(formset.non_form_errors()[0]))
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
    except (ObservationOverlapError, NegativeElevationError, NoTleSetError, SinglePassError,
            ValidationError, ValueError) as error:
        messages.error(request, str(error))
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

    try:
        # Check if there is a TLE available for this satellite
        tle_set = get_tle_set_by_norad_id(sat.norad_cat_id)
        if tle_set:
            tle = tle_set[0]
        else:
            data = [{'error': 'No TLEs for this satellite yet.'}]
            return JsonResponse(data, safe=False)

        # Check the selected transmitter exists, and if yes,
        # store this transmitter in the downlink variable
        transmitter = get_transmitter_by_uuid(params['transmitter'])
        if not transmitter:
            data = [{'error': 'You should select a valid Transmitter.'}]
            return JsonResponse(data, safe=False)
        downlink = transmitter[0]['downlink_low']
    except DBConnectionError as error:
        data = [{'error': str(error)}]
        return JsonResponse(data, safe=False)

    # Fetch all available ground stations
    stations = Station.objects.filter(status__gt=0).prefetch_related(
        Prefetch(
            'observations',
            queryset=Observation.objects.filter(end__gt=now()),
            to_attr='scheduled_obs'
        ), 'antennas', 'antennas__frequency_ranges'
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


@ajax_required
def pass_predictions(request, station_id):
    """Endpoint for pass predictions"""
    station = get_object_or_404(
        Station.objects.prefetch_related(
            Prefetch(
                'observations',
                queryset=Observation.objects.filter(end__gt=now()),
                to_attr='scheduled_obs'
            ), 'antennas', 'antennas__frequency_ranges'
        ),
        id=station_id
    )

    satellites = Satellite.objects.filter(status='alive')

    nextpasses = []
    start = make_aware(datetime.utcnow(), utc)
    end = make_aware(datetime.utcnow() + timedelta(hours=settings.STATION_UPCOMING_END), utc)
    observation_min_start = (
        datetime.utcnow() + timedelta(minutes=settings.OBSERVATION_DATE_MIN_START)
    ).strftime("%Y-%m-%d %H:%M:%S.%f")

    available_transmitter_and_tle_sets = True
    try:
        all_transmitters = get_transmitters_by_status('active')
        all_tle_sets = get_tle_sets()
    except DBConnectionError:
        available_transmitter_and_tle_sets = False

    if available_transmitter_and_tle_sets:
        for satellite in satellites:
            # look for a match between transmitters from the satellite and
            # ground station antenna frequency capabilities
            norad_id = satellite.norad_cat_id
            transmitters = [
                t for t in all_transmitters if t['norad_cat_id'] == norad_id
                and is_transmitter_in_station_range(t, station)  # noqa: W503
            ]
            tle = next(
                (tle_set for tle_set in all_tle_sets if tle_set["norad_cat_id"] == norad_id), None
            )

            if not transmitters or not tle:
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
                        'unknown_rate': str(satellite_stats['unknown_rate']),
                        'future_rate': str(satellite_stats['future_rate']),
                        'total_count': str(satellite_stats['total_count']),
                        'good_count': str(satellite_stats['good_count']),
                        'bad_count': str(satellite_stats['bad_count']),
                        'unknown_count': str(satellite_stats['unknown_count']),
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
        data = [{'error': str(error)}]
        return JsonResponse(data, safe=False)

    stations = Station.objects.filter(status__gt=0
                                      ).prefetch_related('antennas', 'antennas__frequency_ranges')
    available_stations = get_available_stations(stations, downlink, request.user)
    data = {
        'stations': StationSerializer(available_stations, many=True).data,
    }
    return JsonResponse(data, safe=False)


@require_POST
def transmitters_view(request):
    """Returns a transmitter JSON object with information and statistics"""
    norad_id = request.POST.get('satellite', None)
    station_id = request.POST.get('station_id', None)
    try:
        if norad_id:
            Satellite.objects.get(norad_cat_id=norad_id)
        else:
            data = {'error': 'Satellite not provided.'}
            return JsonResponse(data, safe=False)
    except Satellite.DoesNotExist:
        data = {'error': 'Unable to find that satellite.'}
        return JsonResponse(data, safe=False)

    try:
        transmitters = get_transmitters_by_norad_id(norad_id)
    except DBConnectionError as error:
        data = [{'error': str(error)}]
        return JsonResponse(data, safe=False)

    transmitters = [
        t for t in transmitters if t['status'] == 'active' and t['downlink_low'] is not None
    ]
    if station_id:
        supported_transmitters = []
        station = Station.objects.prefetch_related('antennas', 'antennas__frequency_ranges').get(
            id=station_id
        )
        for transmitter in transmitters:
            transmitter_supported = is_transmitter_in_station_range(transmitter, station)
            if transmitter_supported:
                supported_transmitters.append(transmitter)
        transmitters = supported_transmitters

    data = {'transmitters': transmitters_with_stats(transmitters)}

    return JsonResponse(data, safe=False)
