"""Django database base model for SatNOGS Network"""
import os
import struct

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.utils.timezone import now
from tinytag import TinyTag, TinyTagException

from network.base.models import Observation, Station, StationStatusLog
from network.base.rating_tasks import rate_observation
from network.base.tasks import archive_audio, delay_task_with_lock


def _observation_post_save(sender, instance, created, **kwargs):  # pylint: disable=W0613
    """
    Post save Observation operations
    * Check audio file for duration less than 1 sec
    * Validate audio file
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
                rate_observation(instance.id, 'audio_upload', audio_metadata.duration)
        except TinyTagException:
            # Remove invalid audio file
            instance.payload.delete()
        except (struct.error, TypeError):
            # Remove audio file with wrong structure
            instance.payload.delete()
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


def _station_pre_delete(sender, instance, **kwargs):  # pylint: disable=W0613
    """
    Pre delete Station operations
    * Delete future observation of deleted station
    """
    instance.observations.filter(start__gte=now()).delete()


post_save.connect(_observation_post_save, sender=Observation)

post_save.connect(_station_post_save, sender=Station)

pre_delete.connect(_station_pre_delete, sender=Station)
