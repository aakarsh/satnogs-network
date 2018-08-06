from __future__ import absolute_import

import os

from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network.settings')

from django.conf import settings  # noqa

RUN_DAILY = 60 * 60 * 24
RUN_HOURLY = 60 * 60

app = Celery('network')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    from network.base.tasks import (update_all_tle, fetch_data, clean_observations,
                                    station_status_update, stations_cache_rates)

    sender.add_periodic_task(RUN_HOURLY, update_all_tle.s(),
                             name='update-all-tle')

    sender.add_periodic_task(RUN_HOURLY, fetch_data.s(),
                             name='fetch-data')

    sender.add_periodic_task(RUN_HOURLY, station_status_update.s(),
                             name='station-status-update')

    sender.add_periodic_task(RUN_HOURLY, clean_observations.s(),
                             name='clean-observations')

    sender.add_periodic_task(RUN_HOURLY, stations_cache_rates.s(),
                             name='stations-cache-rates')
