"""SatNOGS Network celery task workers"""
from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings  # noqa

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network.settings')

RUN_DAILY = 60 * 60 * 24
RUN_EVERY_TWO_HOURS = 2 * 60 * 60
RUN_HOURLY = 60 * 60
RUN_EVERY_MINUTE = 60
RUN_TWICE_HOURLY = 60 * 30

APP = Celery('network')

APP.config_from_object('django.conf:settings', namespace='CELERY')
APP.autodiscover_tasks()


# Wrapper tasks as workaround for registering shared tasks to beat scheduler
# See https://github.com/celery/celery/issues/5059
# and https://github.com/celery/celery/issues/3797#issuecomment-422656038
@APP.task
def update_all_tle():
    """Wrapper task for 'update_all_tle' shared task"""
    from network.base.tasks import update_all_tle as periodic_task  # pylint: disable=C0415
    periodic_task()


@APP.task
def fetch_data():
    """Wrapper task for 'fetch_data' shared task"""
    from network.base.tasks import fetch_data as periodic_task  # pylint: disable=C0415
    periodic_task()


@APP.task
def clean_observations():
    """Wrapper task for 'clean_observations' shared task"""
    from network.base.tasks import clean_observations as periodic_task  # pylint: disable=C0415
    periodic_task()


@APP.task
def station_status_update():
    """Wrapper task for 'station_status_update' shared task"""
    from network.base.tasks import station_status_update as periodic_task  # pylint: disable=C0415
    periodic_task()


@APP.task
def stations_cache_rates():
    """Wrapper task for 'stations_cache_rates' shared task"""
    from network.base.tasks import stations_cache_rates as periodic_task  # pylint: disable=C0415
    periodic_task()


@APP.task
def notify_for_stations_without_results():
    """Wrapper task for 'notify_for_stations_without_results' shared task"""
    from network.base.tasks import notify_for_stations_without_results as \
        periodic_task  # pylint: disable=C0415
    periodic_task()


@APP.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pylint: disable=W0613
    """Initializes celery tasks that need to run on a scheduled basis"""
    sender.add_periodic_task(RUN_EVERY_TWO_HOURS, update_all_tle.s(), name='update-all-tle')

    sender.add_periodic_task(RUN_HOURLY, fetch_data.s(), name='fetch-data')

    sender.add_periodic_task(RUN_HOURLY, station_status_update.s(), name='station-status-update')

    sender.add_periodic_task(RUN_HOURLY, clean_observations.s(), name='clean-observations')

    sender.add_periodic_task(RUN_HOURLY, stations_cache_rates.s(), name='stations-cache-rates')

    sender.add_periodic_task(
        settings.OBS_NO_RESULTS_CHECK_PERIOD,
        notify_for_stations_without_results.s(),
        name='notify_for_stations_without_results'
    )
