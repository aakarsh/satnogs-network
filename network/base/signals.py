"""Django database base model for SatNOGS Network"""
from django.db.models.signals import post_save, pre_delete
from django.utils.timezone import now

from network.base.models import Station, StationStatusLog


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


post_save.connect(_station_post_save, sender=Station)

pre_delete.connect(_station_pre_delete, sender=Station)
