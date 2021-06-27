"""Django base views for SatNOGS Network"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.generic import ListView

from network.base.db_api import DBConnectionError, get_transmitters_by_norad_id
from network.base.decorators import ajax_required
from network.base.models import Observation, Satellite, Station
from network.base.perms import delete_perms, schedule_perms, vet_perms
from network.base.rating_tasks import rate_observation
from network.base.stats import satellite_stats_by_transmitter_list, transmitters_with_stats
from network.base.utils import community_get_discussion_details
from network.users.models import User


class ObservationListView(ListView):  # pylint: disable=R0901
    """
    Displays a list of observations with pagination
    """
    model = Observation
    context_object_name = "observations"
    paginate_by = settings.ITEMS_PER_PAGE
    template_name = 'base/observations.html'
    str_filters = ['norad', 'observer', 'station', 'start', 'end']
    flag_filters = ['bad', 'good', 'unknown', 'future', 'failed']
    filtered = None

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
        Optionally filter based on future/good/bad/unknown/failed
        """
        filter_params = self.get_filter_params()

        results = self.request.GET.getlist('results')
        rated = self.request.GET.getlist('rated')

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
                        filter_params['bad'], filter_params['good'], filter_params['unknown'],
                        filter_params['future'], filter_params['failed']
                    ]
                )
            ) or results or rated or filter_dict
        )

        observations = observations.filter(**filter_dict)

        if not filter_params['failed']:
            observations = observations.exclude(status__lt=-100)
        if not filter_params['bad']:
            observations = observations.exclude(status__range=(-100, -1))
        if not filter_params['unknown']:
            observations = observations.exclude(status__range=(0, 99), end__lte=now())
        if not filter_params['future']:
            observations = observations.exclude(end__gt=now())
        if not filter_params['good']:
            observations = observations.exclude(status__gte=100)

        if results:
            if 'w0' in results:
                observations = observations.filter(waterfall='')
            elif 'w1' in results:
                observations = observations.exclude(waterfall='')
            if 'a0' in results:
                observations = observations.filter(archived=False, payload='')
            elif 'a1' in results:
                observations = observations.exclude(archived=False, payload='')
            if 'd0' in results:
                observations = observations.filter(demoddata__payload_demod__isnull=True)
            elif 'd1' in results:
                observations = observations.exclude(demoddata__payload_demod__isnull=True)

        if rated:
            if 'rwu' in rated:
                observations = observations.filter(waterfall_status__isnull=True
                                                   ).exclude(waterfall='')
            elif 'rw1' in rated:
                observations = observations.filter(waterfall_status=True)
            elif 'rw0' in rated:
                observations = observations.filter(waterfall_status=False)
        return observations

    def get_context_data(self, **kwargs):  # pylint: disable=W0221
        """
        Need to add a list of satellites to the context for the template
        """
        context = super().get_context_data(**kwargs)
        context['satellites'] = Satellite.objects.all()
        context['authors'] = User.objects.filter(
            observations__isnull=False
        ).distinct().order_by('first_name', 'last_name', 'username')
        context['stations'] = Station.objects.all().order_by('id')
        norad_cat_id = self.request.GET.get('norad', None)
        observer = self.request.GET.get('observer', None)
        station = self.request.GET.get('station', None)
        start = self.request.GET.get('start', None)
        end = self.request.GET.get('end', None)
        context['future'] = self.request.GET.get('future', '1')
        context['bad'] = self.request.GET.get('bad', '1')
        context['good'] = self.request.GET.get('good', '1')
        context['unknown'] = self.request.GET.get('unknown', '1')
        context['failed'] = self.request.GET.get('failed', '1')
        context['results'] = self.request.GET.getlist('results')
        context['rated'] = self.request.GET.getlist('rated')
        context['filtered'] = bool(self.filtered)
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
            'https:%2F%2F{}{}'.format(request.get_host(), request.path)
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
def waterfall_vet(request, observation_id):
    """Handles request for vetting a waterfall"""
    try:
        observation = Observation.objects.get(id=observation_id)
    except Observation.DoesNotExist:
        data = {'error': 'Observation does not exist.'}
        return JsonResponse(data, safe=False)

    status = request.POST.get('status', None)
    can_vet = vet_perms(request.user, observation)

    if not can_vet:
        data = {'error': 'Permission denied.'}
        return JsonResponse(data, safe=False)
    if not observation.has_waterfall:
        data = {'error': 'Observation without waterfall.'}
        return JsonResponse(data, safe=False)

    if status not in ['with-signal', 'without-signal', 'unknown']:
        data = {
            'error': 'Invalid status, select one of \'with-signal\', \'without-signal\' and '
            '\'unknown\'.'
        }
        return JsonResponse(data, safe=False)

    if status == 'with-signal':
        observation.waterfall_status = True
    elif status == 'without-signal':
        observation.waterfall_status = False
    elif status == 'unknown':
        observation.waterfall_status = None

    observation.waterfall_status_user = request.user
    observation.waterfall_status_datetime = now()
    observation.save(
        update_fields=['waterfall_status', 'waterfall_status_user', 'waterfall_status_datetime']
    )
    (observation_status, observation_status_label, observation_status_display
     ) = rate_observation(observation.id, 'set_waterfall_status', observation.waterfall_status)
    data = {
        'waterfall_status_user': observation.waterfall_status_user.displayname,
        'waterfall_status_datetime': observation.waterfall_status_datetime.
        strftime('%Y-%m-%d %H:%M:%S'),
        'waterfall_status': observation.waterfall_status,
        'waterfall_status_label': observation.waterfall_status_label,
        'waterfall_status_display': observation.waterfall_status_display,
        'status': observation_status,
        'status_label': observation_status_label,
        'status_display': observation_status_display,
    }
    return JsonResponse(data, safe=False)


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
        data = [{'error': str(error)}]
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
        'unknown_count': satellite_stats['unknown_count'],
        'future_count': satellite_stats['future_count'],
        'total_count': satellite_stats['total_count'],
        'transmitters': transmitters_with_stats(transmitters)
    }

    return JsonResponse(data, safe=False)
