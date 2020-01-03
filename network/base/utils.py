"""Miscellaneous functions for SatNOGS Network"""
from __future__ import absolute_import

import csv
import urllib
import urllib2
from builtins import str
from datetime import datetime

import requests  # pylint: disable=C0412
from django.conf import settings
from django.contrib.admin.helpers import label_for_field
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.text import slugify
from requests.exceptions import HTTPError, ReadTimeout, RequestException

from network.base.models import DemodData


def export_as_csv(modeladmin, request, queryset):
    """Exports admin panel table in csv format"""
    if not request.user.is_staff:
        raise PermissionDenied
    field_names = modeladmin.list_display
    if 'action_checkbox' in field_names:
        field_names.remove('action_checkbox')

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename={}.csv'.format(
        str(modeladmin.model._meta).replace('.', '_')
    )

    writer = csv.writer(response)
    headers = []
    for field_name in list(field_names):
        label = label_for_field(field_name, modeladmin.model, modeladmin)
        if label.islower():
            label = label.title()
        headers.append(label)
    writer.writerow(headers)
    for row in queryset:
        values = []
        for field in field_names:
            try:
                value = (getattr(row, field))
            except AttributeError:
                value = (getattr(modeladmin, field))
            if callable(value):
                try:
                    # get value from model
                    value = value()
                except Exception:
                    # get value from modeladmin e.g: admin_method_1
                    value = value(row)
            if value is None:
                value = ''
            values.append(str(value))
        writer.writerow(values)
    return response


def export_station_status(self, request, queryset):
    """Exports status of selected stations in csv format"""
    meta = self.model._meta
    field_names = ["id", "status"]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response


def sync_demoddata_to_db(frame_id):
    """Task to send a frame from SatNOGS Network to SatNOGS DB"""
    frame = DemodData.objects.get(id=frame_id)
    obs = frame.observation
    sat = obs.satellite
    ground_station = obs.ground_station

    # need to abstract the timestamp from the filename. hacky..
    file_datetime = frame.payload_demod.name.split('/')[2].split('_')[2]
    frame_datetime = datetime.strptime(file_datetime, '%Y-%m-%dT%H-%M-%S')
    submit_datetime = datetime.strftime(frame_datetime, '%Y-%m-%dT%H:%M:%S.000Z')

    # SiDS parameters
    params = {}
    params['noradID'] = sat.norad_cat_id
    params['source'] = ground_station.name
    params['timestamp'] = submit_datetime
    params['locator'] = 'longLat'
    params['longitude'] = ground_station.lng
    params['latitude'] = ground_station.lat
    params['frame'] = frame.display_payload_hex().replace(' ', '')
    params['satnogs_network'] = 'True'  # NOT a part of SiDS

    apiurl = settings.DB_API_ENDPOINT
    telemetry_url = "{0}telemetry/".format(apiurl)

    try:
        res = urllib2.urlopen(telemetry_url, urllib.urlencode(params))
        code = str(res.getcode())
        if code.startswith('2'):
            frame.copied_to_db = True
            frame.save()
    except (ReadTimeout, HTTPError):
        return


def community_get_discussion_details(
        observation_id, satellite_name, norad_cat_id, observation_url
):
    """
    Return the details of a discussion of the observation (if existent) in the
    satnogs community (discourse)
    """

    discussion_url = ('https://community.libre.space/new-topic?title=Observation {0}: {1}'
                      ' ({2})&body=Regarding [Observation {3}]({4}) ...'
                      '&category=observations') \
        .format(observation_id, satellite_name,
                norad_cat_id, observation_id, observation_url)

    discussion_slug = 'https://community.libre.space/t/observation-{0}-{1}-{2}' \
        .format(observation_id, slugify(satellite_name),
                norad_cat_id)

    try:
        response = requests.get(
            '{}.json'.format(discussion_slug), timeout=settings.COMMUNITY_TIMEOUT
        )
        response.raise_for_status()
        has_comments = (response.status_code == 200)
    except RequestException:
        # Community is unreachable
        has_comments = False

    return {'url': discussion_url, 'slug': discussion_slug, 'has_comments': has_comments}
