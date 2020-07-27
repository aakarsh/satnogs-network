"""Observation rating functions for SatNOGS Network"""
from celery import shared_task
from django.db import transaction

from network.base.models import Observation


@shared_task
def rate_observation(observation_id, action, action_value=None):
    """
    Return status value for given observation and action

    Logic of returned value of action "set_waterfall_status":

                With  Without Unknown
        Failed  100   same    same
        Bad     100   same    1
        Unknown 100   -100    1
        Good    100   -100    1

    """
    observations = Observation.objects.select_for_update()
    with transaction.atomic():
        observation = observations.get(pk=observation_id)
        if action == "set_waterfall_status":
            if action_value:
                return 100
            if action_value is None and observation.status >= -100:
                return 1
            if not action_value and observation.status >= 0:
                return -100
        return observation.status
