import requests

from django.conf import settings

db_api_url = settings.DB_API_ENDPOINT


def transmitters_api_request(url):
    if len(db_api_url) == 0:
        return None
    try:
        request = requests.get(url)
    except requests.exceptions.RequestException:
        return None
    return request.json()


def get_transmitter_by_uuid(uuid):
    transmitters_url = "{}transmitters/?uuid={}".format(db_api_url, uuid)
    return transmitters_api_request(transmitters_url)


def get_transmitters_by_norad_id(norad_id):
    transmitters_url = "{}transmitters/?satellite__norad_cat_id={}".format(db_api_url, norad_id)
    return transmitters_api_request(transmitters_url)


def get_transmitters_by_status(status):
    transmitters_url = "{}transmitters/?status={}".format(db_api_url, status)
    return transmitters_api_request(transmitters_url)


def get_transmitters():
    transmitters_url = "{}transmitters".format(db_api_url)
    return transmitters_api_request(transmitters_url)
