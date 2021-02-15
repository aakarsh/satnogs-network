"""Observation rating functions for SatNOGS Network"""
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from network.base.models import Observation


@shared_task
def find_and_rate_failed_observations():
    """
    Task for checking failed observations, filters all the observation without artifacts after
    some minutes from the end of the observation. These observations rated as "failed" with value
    "-1000".
    """
    time_limit = now() - timedelta(seconds=settings.OBS_NO_RESULTS_IGNORE_TIME)
    Observation.objects.filter(
        waterfall='',
        archived=False,
        payload='',
        demoddata__payload_demod__isnull=True,
        end__lt=time_limit
    ).exclude(status=-1000).update(status=-1000)


@shared_task
def rate_observation(observation_id, action, action_value=None):
    """
    Rate observation for given observation and action and return the result in all forms (integer,
    label name, display name).


    Logic of returned value of action "set_waterfall_status":

        Action value can be one of (True, False, None) and depending on the current observation
        status returns a value following the table bellow:

                With(True)  Without(False) Unknown(None)
        Failed  100         current        current
        Bad     100         current        0
        Unknown 100         -100           0
        Good    100         -100           0

    Logic of returned value of action "waterfall_upload":

        If waterfall is uploaded and observation status is "failed" then it changes it back to
        "unknown" with value "0". On any other case it returns the current observation status.

    Logic of returned value of action "audio_upload":

        Action value is the duration of the audio file in seconds. If its difference from the
        scheduled duration is over 60 seconds and the observation is not rated as "good" then the
        observation is rated as "failed" with value "-1000". If not and observation status is
        "failed" then it changes it back to "unknown" with value "0". On any other case it returns
        the current observation status.

    Logic of returned value of action "data_upload":

        If transmitter mode is other than "CW" or "FM" then observation is rated as good by
        returning "100". If not and observation status is "failed" then it changes it back to
        "unknown" with value "0". On any other case it returns the current observation status.

    """
    observations = Observation.objects.select_for_update()
    with transaction.atomic():
        observation = observations.get(pk=observation_id)
        status = observation.status
        if action == "set_waterfall_status":
            if action_value:
                status = 100
            elif action_value is None and observation.status >= -100:
                status = 0
            elif not action_value and observation.status >= 0:
                status = -100
        elif action == "waterfall_upload":
            if observation.status == -1000:
                status = 0
        elif action == "audio_upload":
            scheduled_duration = observation.end - observation.start
            if abs(scheduled_duration.seconds - action_value) > 60 and observation.status < 100:
                status = -1000
            elif observation.status == -1000:
                status = 0
        elif action == "data_upload":
            if observation.transmitter_mode not in ['CW', 'FM']:
                status = 100
            elif observation.status == -1000:
                status = 0
        observation.status = status
        observation.save(update_fields=['status'])
        return (observation.status, observation.status_label, observation.status_display)
