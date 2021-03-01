"""SatNOGS Network Celery task functions"""
import logging
import os
import struct
import zipfile
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from internetarchive import upload
from internetarchive.exceptions import AuthenticationError
from tinytag import TinyTag, TinyTagException

from network.base.db_api import DBConnectionError, get_tle_sets_by_norad_id_set
from network.base.models import DemodData, Observation, Satellite, Station
from network.base.rating_tasks import rate_observation
from network.base.utils import sync_demoddata_to_db

LOGGER = logging.getLogger('db')


def delay_task_with_lock(task, lock_id, lock_expiration, *args):
    """Ensure unique run of a task by aquiring lock"""
    if cache.add('{0}-{1}'.format(task.name, lock_id), '', lock_expiration):
        task.delay(*args)


def get_observation_zip_group(observation_id):
    """ Return observation group """
    return (observation_id - 1) // settings.AUDIO_FILES_PER_ZIP


def get_zip_range_and_path(group):
    """ Return range and zip filepath for a group of observation IDs """
    group *= settings.AUDIO_FILES_PER_ZIP
    group_range = (group + 1, group + settings.AUDIO_FILES_PER_ZIP)
    zip_range = '{0}-{1}'.format(str(group_range[0]).zfill(9), str(group_range[1]).zfill(9))
    zip_filename = '{0}-{1}.zip'.format(settings.ZIP_FILE_PREFIX, zip_range)
    zip_path = '{0}/{1}'.format(settings.MEDIA_ROOT, zip_filename)
    return (group_range, zip_path)


@shared_task
def zip_audio(observation_id, path):
    """Add audio file to a zip file"""
    LOGGER.info('zip audio: %s', observation_id)
    group = get_observation_zip_group(observation_id)
    group_range, zip_path = get_zip_range_and_path(group)
    cache_key = '{0}-{1}-{2}'.format('ziplock', group_range[0], group_range[1])
    if cache.add(cache_key, '', settings.ZIP_AUDIO_LOCK_EXPIRATION):
        LOGGER.info('Lock acquired for zip audio: %s', observation_id)
        file_exists_in_zip_file = False
        files_in_zip = []
        if zipfile.is_zipfile(zip_path):
            with zipfile.ZipFile(file=zip_path, mode='r') as zip_file:
                files_in_zip = zip_file.namelist()
                filename = path.split('/')[-1]
                if filename in files_in_zip:
                    file_exists_in_zip_file = True
        if file_exists_in_zip_file:
            LOGGER.info('Audio file already exists in zip file for id %s', observation_id)
            ids = [name.split('_')[1] for name in files_in_zip]
            observations = Observation.objects.filter(pk__in=ids).exclude(payload=''
                                                                          ).exclude(archived=True)
            if observations.count() == len(ids):
                observations.update(audio_zipped=False)
                os.remove(zip_path)
            else:
                cache.delete(cache_key)
                error_message = (
                    'Zip file can not be deleted,'
                    ' it includes removed, archived or duplicate audio files'
                )
                raise RuntimeError(error_message)
        else:
            with zipfile.ZipFile(file=zip_path, mode='a', compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=9) as zip_file:
                zip_file.write(filename=path, arcname=path.split('/')[-1])
            Observation.objects.filter(pk=observation_id).update(audio_zipped=True)
        cache.delete(cache_key)


@shared_task
def process_audio(observation_id, force_zip=False):
    """
    Process Audio
    * Check audio file for duration less than 1 sec
    * Validate audio file
    * Run task for rating according to audio file
    * Run task for adding audio in zip file
    """
    LOGGER.info('process audio: %s', observation_id)
    observations = Observation.objects.select_for_update()
    with transaction.atomic():
        observation = observations.get(pk=observation_id)
        try:
            audio_metadata = TinyTag.get(observation.payload.path)
            # Remove audio if it is less than 1 sec
            if audio_metadata.duration is None or audio_metadata.duration < 1:
                observation.payload.delete()
                return
            rate_observation.delay(observation_id, 'audio_upload', audio_metadata.duration)
            if settings.ZIP_AUDIO_FILES or force_zip:
                zip_audio(observation_id, observation.payload.path)
        except TinyTagException:
            # Remove invalid audio file
            observation.payload.delete()
            return
        except (struct.error, TypeError):
            # Remove audio file with wrong structure
            observation.payload.delete()
            return


@shared_task
def zip_audio_files(force_zip=False):
    """Zip audio files per group"""
    LOGGER.info('zip audio')
    if cache.add('zip-task', '', settings.ZIP_TASK_LOCK_EXPIRATION):
        LOGGER.info('Lock acquired for zip task')
        if settings.ZIP_AUDIO_FILES or force_zip:
            zipped_files = []
            observations = Observation.objects.filter(audio_zipped=False).exclude(payload='')
            non_zipped_ids = observations.order_by('pk').values_list('pk', flat=True)
            if non_zipped_ids:
                group = get_observation_zip_group(non_zipped_ids[0])
            for observation_id in non_zipped_ids:
                if group == get_observation_zip_group(observation_id):
                    process_audio(observation_id, force_zip)
                    zipped_files.append(observation_id)
                else:
                    LOGGER.info('Processed Files: %s', zipped_files)
                    cache.delete('zip-task')
                    return
            LOGGER.info('Processed Files: %s', zipped_files)
    cache.delete('zip-task')


@shared_task
def archive_audio_zip_files(force_archive=False):
    """Archive audio zip files to archive.org"""
    LOGGER.info('archive audio')
    if cache.add('archive-task', '', settings.ARCHIVE_TASK_LOCK_EXPIRATION):
        LOGGER.info('Lock acquired for archive task')
        if settings.ARCHIVE_ZIP_FILES or force_archive:
            archived_groups = []
            skipped_groups = []
            archive_skip_time = now() - timedelta(hours=settings.ARCHIVE_SKIP_TIME)
            observation_ids = Observation.objects.filter(
                audio_zipped=True, archived=False
            ).values_list(
                'pk', flat=True
            )
            groups = {get_observation_zip_group(pk) for pk in observation_ids}
            for group in groups:
                group_range, zip_path = get_zip_range_and_path(group)
                cache_key = '{0}-{1}-{2}'.format('ziplock', group_range[0], group_range[1])
                if (not cache.add(cache_key, '', settings.ARCHIVE_ZIP_LOCK_EXPIRATION)
                    ) or Observation.objects.filter(pk__range=group_range).filter(Q(
                        archived=True) | Q(end__gte=archive_skip_time) | (~Q(payload='') & Q(
                            audio_zipped=False))).exists() or not zipfile.is_zipfile(zip_path):
                    skipped_groups.append(group_range)
                    cache.delete(cache_key)
                    continue

                archived_groups.append(group_range)
                site = Site.objects.get_current()
                license_url = 'http://creativecommons.org/licenses/by-sa/4.0/'

                item_group = group // settings.ZIP_FILES_PER_ITEM
                files_per_item = settings.ZIP_FILES_PER_ITEM * settings.AUDIO_FILES_PER_ZIP
                item_from = (item_group * files_per_item) + 1
                item_to = (item_group + 1) * files_per_item
                item_range = '{0}-{1}'.format(str(item_from).zfill(9), str(item_to).zfill(9))

                item_id = '{0}-{1}'.format(settings.ITEM_IDENTIFIER_PREFIX, item_range)
                title = '{0} {1}'.format(settings.ITEM_TITLE_PREFIX, item_range)
                description = (
                    '<p>Audio files from <a href="{0}/observations">'
                    'SatNOGS Observations</a> with ID from {1} to {2}.</p>'
                ).format(site.domain, item_from, item_to)

                item_metadata = dict(
                    collection=settings.ARCHIVE_COLLECTION,
                    title=title,
                    mediatype=settings.ARCHIVE_MEDIA_TYPE,
                    licenseurl=license_url,
                    description=description
                )

                zip_name = zip_path.split('/')[-1]
                file_metadata = dict(
                    name=zip_path,
                    title=zip_name.replace('.zip', ''),
                    license_url=license_url,
                )

                try:
                    res = upload(
                        item_id,
                        files=file_metadata,
                        metadata=item_metadata,
                        access_key=settings.S3_ACCESS_KEY,
                        secret_key=settings.S3_SECRET_KEY,
                        retries=settings.S3_RETRIES_ON_SLOW_DOWN,
                        retries_sleep=settings.S3_RETRIES_SLEEP
                    )
                except (requests.exceptions.RequestException, AuthenticationError) as error:
                    LOGGER.info('Upload of zip %s failed, reason:\n%s', zip_name, repr(error))
                    return

                if res[0].status_code == 200:
                    observations = Observation.objects.select_for_update().filter(
                        pk__range=group_range
                    ).filter(audio_zipped=True)
                    with transaction.atomic():
                        for observation in observations:
                            audio_filename = observation.payload.path.split('/')[-1]
                            observation.archived = True
                            observation.archive_url = '{0}{1}/{2}/{3}'.format(
                                settings.ARCHIVE_URL, item_id, zip_name, audio_filename
                            )
                            observation.archive_identifier = item_id
                            if settings.REMOVE_ARCHIVED_AUDIO_FILES:
                                observation.payload.delete(save=False)
                            observation.save(
                                update_fields=[
                                    'archived', 'archive_url', 'archive_identifier', 'payload'
                                ]
                            )
                    if settings.REMOVE_ARCHIVED_ZIP_FILE:
                        os.remove(zip_path)
                cache.delete(cache_key)
            cache.delete('archive-task')
            LOGGER.info('Archived Groups: %s', archived_groups)
            LOGGER.info('Skipped Groups: %s', skipped_groups)


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
        LOGGER.info("Zero length api url, fetching is stopped")
        return
    satellites_url = "{}satellites".format(db_api_url)

    LOGGER.info("Fetching Satellites from %s", satellites_url)
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

    LOGGER.info('Added/Updated %s/%s satellites from db.', satellites_added, satellites_updated)


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
