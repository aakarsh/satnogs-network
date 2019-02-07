import csv
import urllib
import urllib2
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.contrib.admin.helpers import label_for_field
from django.conf import settings
from requests.exceptions import ReadTimeout, HTTPError
from network.base.models import DemodData
from datetime import datetime


def export_as_csv(modeladmin, request, queryset):
    if not request.user.is_staff:
        raise PermissionDenied
    opts = modeladmin.model._meta
    field_names = modeladmin.list_display
    if 'action_checkbox' in field_names:
        field_names.remove('action_checkbox')

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % unicode(opts)\
                                      .replace('.', '_')

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
            values.append(unicode(value).encode('utf-8'))
        writer.writerow(values)
    return response


def demod_to_db(frame_id):
    """Task to send a frame from SatNOGS network to SatNOGS db"""
    frame = DemodData.objects.get(id=frame_id)
    obs = frame.observation
    sat = obs.satellite
    ground_station = obs.ground_station

    # need to abstract the timestamp from the filename. hacky..
    file_datetime = frame.payload_demod.name.split('/')[2].split('_')[2]
    frame_datetime = datetime.strptime(file_datetime, '%Y-%m-%dT%H-%M-%S')
    submit_datetime = datetime.strftime(frame_datetime,
                                        '%Y-%m-%dT%H:%M:%S.000Z')

    # SiDS parameters
    params = {}
    params['noradID'] = sat.norad_cat_id
    params['source'] = ground_station.name
    params['timestamp'] = submit_datetime
    params['locator'] = 'longLat'
    params['longitude'] = ground_station.lng
    params['latitude'] = ground_station.lat
    params['frame'] = frame.display_payload().replace(' ', '')
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
