"""Django database base model for SatNOGS Network"""
from __future__ import absolute_import, division

import os
import struct
from datetime import timedelta

from django.conf import settings
from django.db.models.signals import post_save
from django.utils.timezone import now
from tinytag import TinyTag, TinyTagException

from network.base.models import Observation, Station, StationStatusLog, Tle
from network.base.tasks import archive_audio, delay_task_with_lock


def _observation_post_save(sender, instance, created, **kwargs):  # pylint: disable=W0613
    """
    Post save Observation operations
    * Check audio file for duration less than 1 sec
    * Validate audio file
    * Auto vet as good observation with DemodData
    * Mark Observations from testing stations
    * Run task for archiving audio
    """
    post_save.disconnect(_observation_post_save, sender=Observation)
    if instance.has_audio and not instance.archived:
        try:
            audio_metadata = TinyTag.get(instance.payload.path)
            # Remove audio if it is less than 1 sec
            if audio_metadata.duration is None or audio_metadata.duration < 1:
                instance.payload.delete()
            elif settings.ENVIRONMENT == 'production' and os.path.isfile(instance.payload.path):
                delay_task_with_lock(
                    archive_audio, instance.id, settings.ARCHIVE_AUDIO_LOCK_EXPIRATION, instance.id
                )
        except TinyTagException:
            # Remove invalid audio file
            instance.payload.delete()
        except (struct.error, TypeError):
            # Remove audio file with wrong structure
            instance.payload.delete()
    if created and instance.ground_station.testing:
        instance.testing = True
        instance.save()
    post_save.connect(_observation_post_save, sender=Observation)


def _station_post_save(sender, instance, created, **kwargs):  # pylint: disable=W0613
    """
    Post save Station operations
    * Store current status
    """
    post_save.disconnect(_station_post_save, sender=Station)
    if not created:
        current_status = instance.status
        if instance.is_offline:
            instance.status = 0
        elif instance.testing:
            instance.status = 1
        else:
            instance.status = 2
        instance.save()
        if instance.status != current_status:
            StationStatusLog.objects.create(station=instance, status=instance.status)
    else:
        StationStatusLog.objects.create(station=instance, status=instance.status)
    post_save.connect(_station_post_save, sender=Station)


def _tle_post_save(sender, instance, created, **kwargs):  # pylint: disable=W0613
    """
    Post save Tle operations
    * Update TLE for future observations
    """
    if created:
        start = now() + timedelta(minutes=10)
        Observation.objects.filter(satellite=instance.satellite, start__gt=start) \
                           .update(tle=instance.id)


post_save.connect(_observation_post_save, sender=Observation)

post_save.connect(_station_post_save, sender=Station)

post_save.connect(_tle_post_save, sender=Tle)
