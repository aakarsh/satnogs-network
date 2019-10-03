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
APP.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@APP.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pylint: disable=W0613
    from network.base.tasks import (
        update_all_tle, fetch_data, clean_observations, station_status_update,
        stations_cache_rates, notify_for_stations_without_results, sync_to_db
    )

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

    sender.add_periodic_task(RUN_TWICE_HOURLY, sync_to_db.s(), name='sync-to-db')
