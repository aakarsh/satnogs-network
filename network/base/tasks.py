"""SatNOGS Network Celery task functions"""
import os
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.timezone import now
from internetarchive import upload
from internetarchive.exceptions import AuthenticationError

from network.base.db_api import DBConnectionError, get_tle_sets_by_norad_id_set
from network.base.models import DemodData, Observation, Satellite, Station
from network.base.utils import sync_demoddata_to_db


def delay_task_with_lock(task, lock_id, lock_expiration, *args):
    """Ensure unique run of a task by aquiring lock"""
    if cache.add('{0}-{1}'.format(task.name, lock_id), '', lock_expiration):
        task.delay(*args)


@shared_task
def update_future_observations_with_new_tle_sets():
    """ Update future observations with latest TLE sets"""
    start = now() + timedelta(minutes=10)
    future_observations = Observation.objects.filter(start__gt=start)
    norad_id_set = set(future_observations.values_list('satellite__norad_cat_id', flat=True))
    try:
        if norad_id_set:
            tle_sets = get_tle_sets_by_norad_id_set(norad_id_set)
        else:
            return
    except DBConnectionError:
        return
    for norad_id in tle_sets.keys():
        if not tle_sets[norad_id]:
            continue
        tle_set = tle_sets[norad_id][0]
        tle_updated = datetime.strptime(tle_set['updated'], "%Y-%m-%dT%H:%M:%S.%f%z")
        future_observations.filter(
            satellite__norad_cat_id=norad_id, tle_updated__lt=tle_updated
        ).update(
            tle_line_0=tle_set['tle0'],
            tle_line_1=tle_set['tle1'],
            tle_line_2=tle_set['tle2'],
            tle_source=tle_set['tle_source'],
            tle_updated=tle_set['updated'],
        )


@shared_task
def fetch_data():
    """Fetch all satellites and transmitters from SatNOGS DB

       Throws: requests.exceptions.ConectionError"""

    db_api_url = settings.DB_API_ENDPOINT
    if not db_api_url:
        print("Zero length api url, fetching is stopped")
        return
    satellites_url = "{}satellites".format(db_api_url)

    print("Fetching Satellites from {}".format(satellites_url))
    r_satellites = requests.get(satellites_url)

    # Fetch Satellites
    satellites_added = 0
    satellites_updated = 0
    for satellite in r_satellites.json():
        norad_cat_id = satellite['norad_cat_id']
        satellite.pop('decayed', None)
        satellite.pop('launched', None)
        satellite.pop('deployed', None)
        satellite.pop('website', None)
        satellite.pop('operator', None)
        satellite.pop('countries', None)
        try:
            # Update Satellite
            existing_satellite = Satellite.objects.get(norad_cat_id=norad_cat_id)
            existing_satellite.__dict__.update(satellite)
            existing_satellite.save()
            satellites_updated += 1
        except Satellite.DoesNotExist:
            # Add Satellite
            satellite.pop('telemetries', None)
            Satellite.objects.create(**satellite)
            satellites_added += 1

    print('Added/Updated {}/{} satellites from db.'.format(satellites_added, satellites_updated))


@shared_task
def archive_audio(obs_id):
    """Upload audio of observation in archive.org"""
    obs = Observation.objects.get(id=obs_id)
    suffix = '-{0}'.format(settings.ENVIRONMENT)
    if settings.ENVIRONMENT == 'production':
        suffix = ''
    identifier = 'satnogs{0}-observation-{1}'.format(suffix, obs.id)

    ogg = obs.payload.path
    filename = obs.payload.name.split('/')[-1]
    site = Site.objects.get_current()
    description = (
        '<p>Audio file from SatNOGS{0} <a href="{1}/observations/{2}">'
        'Observation {3}</a>.</p>'
    ).format(suffix, site.domain, obs.id, obs.id)
    metadata = dict(
        collection=settings.ARCHIVE_COLLECTION,
        title=identifier,
        mediatype='audio',
        licenseurl='http://creativecommons.org/licenses/by-sa/4.0/',
        description=description
    )
    try:
        res = upload(
            identifier,
            files=[ogg],
            metadata=metadata,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            retries=settings.S3_RETRIES_ON_SLOW_DOWN,
            retries_sleep=settings.S3_RETRIES_SLEEP
        )
    except (requests.exceptions.RequestException, AuthenticationError) as error:
        print('Upload of audio for observation {} failed, reason:\n{}'.format(obs_id, repr(error)))
        return
    if res[0].status_code == 200:
        obs.archived = True
        obs.archive_url = '{0}{1}/{2}'.format(settings.ARCHIVE_URL, identifier, filename)
        obs.archive_identifier = identifier
        obs.payload.delete(save=False)
        obs.save(update_fields=['archived', 'archive_url', 'archive_identifier', 'payload'])


@shared_task
def clean_observations():
    """Task to clean up old observations that lack actual data."""
    threshold = now() - timedelta(days=int(settings.OBSERVATION_OLD_RANGE))
    observations = Observation.objects.filter(end__lt=threshold, archived=False) \
                                      .exclude(payload='')
    for obs in observations:
        if settings.ENVIRONMENT == 'stage':
            if not obs.status >= 100:
                obs.delete()
                continue
        if os.path.isfile(obs.payload.path):
            archive_audio.delay(obs.id)


@shared_task
def sync_to_db(frame_id=None):
    """Task to send demod data to SatNOGS DB / SiDS"""
    frames = DemodData.objects.filter(copied_to_db=False).exclude(
        observation__transmitter_mode__in=settings.NOT_SYNCED_MODES
    )

    if frame_id:
        frames = frames.filter(pk=frame_id)[:1]

    for frame in frames:
        if frame.is_image() or not os.path.isfile(frame.payload_demod.path):
            continue
        try:
            sync_demoddata_to_db(frame)
        except requests.exceptions.RequestException:
            # Sync to db failed, skip this frame for a future task instance
            continue


@shared_task
def station_status_update():
    """Task to update Station status."""
    for station in Station.objects.all():
        if station.is_offline:
            station.status = 0
        elif station.testing:
            station.status = 1
        else:
            station.status = 2
        station.save()


@shared_task
def notify_for_stations_without_results():
    """Task to send email for stations with observations without results."""
    email_to = settings.EMAIL_FOR_STATIONS_ISSUES
    if email_to:
        stations = ''
        obs_limit = settings.OBS_NO_RESULTS_MIN_COUNT
        time_limit = now() - timedelta(seconds=settings.OBS_NO_RESULTS_IGNORE_TIME)
        last_check = time_limit - timedelta(seconds=settings.OBS_NO_RESULTS_CHECK_PERIOD)
        for station in Station.objects.filter(status=2):
            last_obs = Observation.objects.filter(
                ground_station=station, end__lt=time_limit
            ).order_by("-end")[:obs_limit]
            obs_without_results = 0
            obs_after_last_check = False
            for observation in last_obs:
                if not (observation.has_audio and observation.has_waterfall):
                    obs_without_results += 1
                if observation.end >= last_check:
                    obs_after_last_check = True
            if obs_without_results == obs_limit and obs_after_last_check:
                stations += ' ' + str(station.id)
        if stations:
            # Notify user
            subject = '[satnogs] Station with observations without results'
            send_mail(
                subject, stations, settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_FOR_STATIONS_ISSUES], False
            )


@shared_task
def stations_cache_rates():
    """Cache the success rate of the stations"""
    stations = Station.objects.all()
    for station in stations:
        observations = station.observations.exclude(testing=True).exclude(status__range=(0, 99))
        success = observations.filter(
            id__in=(o.id for o in observations if o.status >= 100 or -100 <= o.status < 0)
        ).count()
        if observations:
            rate = int(100 * (success / observations.count()))
            cache.set('station-{0}-rate'.format(station.id), rate, 60 * 60 * 2)
