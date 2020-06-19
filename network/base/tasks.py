"""SatNOGS Network Celery task functions"""
from __future__ import absolute_import, division, print_function

import json
import os
from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Prefetch
from django.utils.timezone import now
from internetarchive import upload
from internetarchive.exceptions import AuthenticationError
from satellite_tle import fetch_tles

from network.base.models import DemodData, LatestTle, Observation, Satellite, \
    Station, Tle, Transmitter
from network.base.utils import sync_demoddata_to_db


def delay_task_with_lock(task, lock_id, lock_expiration, *args):
    """Ensure unique run of a task by aquiring lock"""
    if cache.add('{0}-{1}'.format(task.name, lock_id), '', lock_expiration):
        task.delay(*args)


@shared_task
def update_all_tle():
    """Task to update all satellite TLEs"""
    latest_tle_queryset = LatestTle.objects.all()
    satellites = Satellite.objects.exclude(status='re-entered').exclude(
        manual_tle=True, norad_follow_id__isnull=True
    ).prefetch_related(Prefetch('tles', queryset=latest_tle_queryset, to_attr='tle'))

    # Collect all norad ids we are interested in
    norad_ids = set()
    for obj in satellites:
        norad_id = obj.norad_cat_id
        if obj.manual_tle:
            norad_id = obj.norad_follow_id
        norad_ids.add(int(norad_id))

    # Filter only officially announced NORAD IDs
    catalog_norad_ids = {norad_id for norad_id in norad_ids if norad_id < 99000}

    # Check for TLE custom sources
    other_sources = {}
    if settings.TLE_SOURCES_JSON:
        try:
            sources_json = json.loads(settings.TLE_SOURCES_JSON)
            other_sources['sources'] = list(sources_json.items())
        except json.JSONDecodeError as error:
            print('TLE Sources JSON ignored as it is invalid: {}'.format(error))
    if settings.SPACE_TRACK_USERNAME and settings.SPACE_TRACK_PASSWORD:
        other_sources['spacetrack_config'] = {
            'identity': settings.SPACE_TRACK_USERNAME,
            'password': settings.SPACE_TRACK_PASSWORD
        }

    print("==Fetching TLEs==")
    tles = fetch_tles(catalog_norad_ids, **other_sources)

    for obj in satellites:
        norad_id = obj.norad_cat_id
        if obj.manual_tle:
            norad_id = obj.norad_follow_id

        if norad_id not in list(tles.keys()):
            # No TLE available for this satellite
            print('{} - {}: NORAD ID not found [error]'.format(obj.name, norad_id))
            continue

        source, tle = tles[norad_id]

        if obj.tle and obj.tle[0].tle1 == tle[1]:
            # Stored TLE is already the latest available for this satellite
            print('{} - {}: TLE already exists [defer]'.format(obj.name, norad_id))
            continue

        Tle.objects.create(tle0=tle[0], tle1=tle[1], tle2=tle[2], satellite=obj, tle_source=source)
        print('{} - {} - {}: new TLE found [updated]'.format(obj.name, norad_id, source))


@shared_task
def fetch_data():
    """Fetch all satellites and transmitters from SatNOGS DB

       Throws: requests.exceptions.ConectionError"""

    db_api_url = settings.DB_API_ENDPOINT
    if not db_api_url:
        print("Zero length api url, fetching is stopped")
        return
    satellites_url = "{}satellites".format(db_api_url)
    transmitters_url = "{}transmitters".format(db_api_url)

    print("Fetching Satellites from {}".format(satellites_url))
    r_satellites = requests.get(satellites_url)

    print("Fetching Transmitters from {}".format(transmitters_url))
    r_transmitters = requests.get(transmitters_url)

    # Fetch Satellites
    satellites_added = 0
    satellites_updated = 0
    for satellite in r_satellites.json():
        norad_cat_id = satellite['norad_cat_id']
        satellite.pop('decayed', None)
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

    # Fetch Transmitters
    transmitters_added = 0
    transmitters_skipped = 0
    for transmitter in r_transmitters.json():
        uuid = transmitter['uuid']

        try:
            # Transmitter already exists, skip
            Transmitter.objects.get(uuid=uuid)
            transmitters_skipped += 1
        except Transmitter.DoesNotExist:
            # Create Transmitter
            Transmitter.objects.create(uuid=uuid)
            transmitters_added += 1

    print(
        'Added/Skipped {}/{} transmitters from db.'.format(
            transmitters_added, transmitters_skipped
        )
    )


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
            if not obs.is_good:
                obs.delete()
                continue
        if os.path.isfile(obs.payload.path):
            archive_audio.delay(obs.id)


@shared_task
def sync_to_db(frame_id=None):
    """Task to send demod data to SatNOGS DB / SiDS"""
    transmitters = Transmitter.objects.filter(sync_to_db=True).values_list('uuid', flat=True)

    frames = DemodData.objects.filter(
        copied_to_db=False, observation__transmitter_uuid__in=transmitters
    )

    if frame_id:
        frames = frames.filter(pk=frame_id)[:1]

    for frame in frames:
        if frame.is_image() or frame.copied_to_db or not os.path.isfile(frame.payload_demod.path):
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
        observations = station.observations.exclude(testing=True).exclude(vetted_status="unknown")
        success = observations.filter(
            id__in=(o.id for o in observations if o.is_good or o.is_bad)
        ).count()
        if observations:
            rate = int(100 * (float(success) / float(observations.count())))
            cache.set('station-{0}-rate'.format(station.id), rate, 60 * 60 * 2)
