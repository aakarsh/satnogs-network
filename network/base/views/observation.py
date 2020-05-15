"""Django base views for SatNOGS Network"""
from __future__ import absolute_import

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.generic import ListView

from network.base.db_api import DBConnectionError, get_transmitters_by_norad_id
from network.base.decorators import ajax_required
from network.base.models import Observation, Satellite, Station
from network.base.perms import delete_perms, schedule_perms, vet_perms
from network.base.stats import satellite_stats_by_transmitter_list, \
    transmitters_with_stats
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
    flag_filters = ['bad', 'good', 'unvetted', 'future', 'failed']
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
        context = super(ObservationListView, self).get_context_data(**kwargs)
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
        'unvetted_count': satellite_stats['unvetted_count'],
        'future_count': satellite_stats['future_count'],
        'total_count': satellite_stats['total_count'],
        'transmitters': transmitters_with_stats(transmitters)
    }

    return JsonResponse(data, safe=False)
