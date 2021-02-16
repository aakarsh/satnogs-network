"""Miscellaneous functions for SatNOGS Network"""
import csv
from builtins import str
from datetime import datetime

import requests  # pylint: disable=C0412
from django.conf import settings
from django.contrib.admin.helpers import label_for_field
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.text import slugify
from requests.exceptions import RequestException


def populate_formset_error_messages(messages, request, formset):
    """Add errors to django messages framework by extracting them from formset)"""
    non_form_errors = formset.non_form_errors()
    if non_form_errors:
        messages.error(request, str(non_form_errors[0]))
        return
    for error in formset.errors:
        if error:
            for field in error:
                messages.error(request, str(error[field][0]))
        return


def bands_from_range(min_frequency, max_frequency):
    """Returns band names of the given frequency range based on
    https://www.itu.int/rec/R-REC-V.431-8-201508-I/en recommendation from ITU
    """
    if max_frequency < min_frequency:
        return []

    frequency_bands = {
        'ULF': (300, 3000),
        'VLF': (3000, 30000),
        'LF': (30000, 300000),
        'MF': (300000, 3000000),
        'HF': (3000000, 30000000),
        'VHF': (30000000, 300000000),
        'UHF': (300000000, 1000000000),
        'L': (1000000000, 2000000000),
        'S': (2000000000, 4000000000),
        'C': (4000000000, 8000000000),
        'X': (8000000000, 12000000000),
        'Ku': (12000000000, 18000000000),
        'K': (18000000000, 27000000000),
        'Ka': (27000000000, 40000000000),
    }

    bands = []
    found_min = False

    for name, (min_freq, max_freq) in frequency_bands.items():
        if not found_min:
            if min_freq <= min_frequency <= max_freq:
                bands.append(name)
                if min_freq <= max_frequency <= max_freq:
                    return bands
                found_min = True
                continue
            continue
        bands.append(name)
        if min_freq < max_frequency <= max_freq:
            return bands
    return []


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
                except TypeError:
                    # get value from modeladmin e.g: admin_method_1
                    value = value(row)
            if value is None:
                value = ''
            values.append(str(value).encode('utf-8'))
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


def community_get_discussion_details(
    observation_id, satellite_name, norad_cat_id, observation_url
):
    """
    Return the details of a discussion of the observation (if existent) in the
    satnogs community (discourse)
    """

    discussion_url = ('https://community.libre.space/new-topic?title=Observation {0}: {1}'
                      ' ({2})&body=Regarding [Observation {0}]({3}) ...'
                      '&category=observations') \
        .format(observation_id, satellite_name, norad_cat_id, observation_url)

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


def sync_demoddata_to_db(frame):
    """
    Task to send a frame from SatNOGS Network to SatNOGS DB

    Raises requests.exceptions.RequestException if sync fails."""
    obs = frame.observation
    sat = obs.satellite
    ground_station = obs.ground_station

    try:
        # need to abstract the timestamp from the filename. hacky..
        file_datetime = frame.payload_demod.name.split('/')[2].split('_')[2]
        frame_datetime = datetime.strptime(file_datetime, '%Y-%m-%dT%H-%M-%S')
        submit_datetime = datetime.strftime(frame_datetime, '%Y-%m-%dT%H:%M:%S.000Z')
    except ValueError:
        return

    # SiDS parameters
    params = {
        'noradID': sat.norad_cat_id,
        'source': ground_station.name,
        'timestamp': submit_datetime,
        'locator': 'longLat',
        'longitude': ground_station.lng,
        'latitude': ground_station.lat,
        'frame': frame.display_payload_hex().replace(' ', ''),
        'satnogs_network': 'True',  # NOT a part of SiDS
        'observation_id': obs.id,  # NOT a part of SiDS
        'station_id': obs.ground_station.id  # NOT a part of SiDS
    }

    telemetry_url = "{}telemetry/".format(settings.DB_API_ENDPOINT)

    response = requests.post(telemetry_url, data=params, timeout=settings.DB_API_TIMEOUT)
    response.raise_for_status()

    frame.copied_to_db = True
    frame.save(update_fields=['copied_to_db'])
