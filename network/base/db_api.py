"""SatNOGS Network functions that consume DB API"""
import requests
from django.conf import settings

DB_API_URL = settings.DB_API_ENDPOINT
DB_API_KEY = settings.DB_API_KEY


class DBConnectionError(Exception):
    """Error when there are connection issues with DB API"""


def tle_api_request(url):
    """Perform TLE query on SatNOGS DB API and return the results"""
    headers = {}
    if DB_API_KEY:
        headers['authorization'] = 'Token {0}'.format(DB_API_KEY)
    if not DB_API_URL:
        raise DBConnectionError('Error in DB API connection. Blank DB API URL!')
    try:
        request = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as error:
        raise DBConnectionError('Error in DB API connection. Please try again!') from error
    return request.json()


def get_tle_set_by_norad_id(norad_id):
    """Returns TLE set filtered by NORAD ID"""
    tle_url = "{}tle/?norad_cat_id={}".format(DB_API_URL, norad_id)
    return tle_api_request(tle_url)


def get_tle_sets():
    """Returns TLE sets"""
    tle_url = "{}tle/".format(DB_API_URL)
    return tle_api_request(tle_url)


def get_tle_sets_by_norad_id_set(norad_id_set):
    """Returns TLE sets filtered by NORAD ID list"""
    if not norad_id_set:
        raise ValueError('Expected a non empty list of NORAD IDs.')
    if len(norad_id_set) == 1:
        norad_id = next(iter(norad_id_set))
        tle_set = get_tle_set_by_norad_id(norad_id)
        return {norad_id: tle_set}

    tle_sets_list = get_tle_sets()

    tle_sets = {t['norad_cat_id']: [t] for t in tle_sets_list if t['norad_cat_id'] in norad_id_set}
    found_norad_ids_set = set(tle_sets.keys())
    for norad_id in norad_id_set.difference(found_norad_ids_set):
        tle_sets[norad_id] = []
    return tle_sets


def transmitters_api_request(url):
    """Perform transmitter query on SatNOGS DB API and return the results"""
    if not DB_API_URL:
        raise DBConnectionError('Error in DB API connection. Blank DB API URL!')
    try:
        request = requests.get(url)
    except requests.exceptions.RequestException as error:
        raise DBConnectionError('Error in DB API connection. Please try again!') from error
    return request.json()


def get_transmitter_by_uuid(uuid):
    """Returns transmitter filtered by Transmitter UUID"""
    transmitters_url = "{}transmitters/?uuid={}".format(DB_API_URL, uuid)
    return transmitters_api_request(transmitters_url)


def get_transmitters_by_norad_id(norad_id):
    """Returns transmitters filtered by NORAD ID"""
    transmitters_url = "{}transmitters/?satellite__norad_cat_id={}".format(DB_API_URL, norad_id)
    return transmitters_api_request(transmitters_url)


def get_transmitters_by_status(status):
    """Returns transmitters filtered by status"""
    transmitters_url = "{}transmitters/?status={}".format(DB_API_URL, status)
    return transmitters_api_request(transmitters_url)


def get_transmitters():
    """Returns all transmitters"""
    transmitters_url = "{}transmitters".format(DB_API_URL)
    return transmitters_api_request(transmitters_url)


def get_transmitters_by_uuid_set(uuid_set):
    """Returns transmitters filtered by Transmitter UUID list"""
    if not uuid_set:
        raise ValueError('Expected a non empty list of UUIDs.')
    if len(uuid_set) == 1:
        transmitter_uuid = next(iter(uuid_set))
        transmitter = get_transmitter_by_uuid(transmitter_uuid)
        if not transmitter:
            raise ValueError('Invalid Transmitter UUID: {0}'.format(str(transmitter_uuid)))
        return {transmitter[0]['uuid']: transmitter[0]}

    transmitters_list = get_transmitters()

    transmitters = {t['uuid']: t for t in transmitters_list if t['uuid'] in uuid_set}
    invalid_transmitters = [str(uuid) for uuid in uuid_set.difference(set(transmitters.keys()))]

    if not invalid_transmitters:
        return transmitters

    if len(invalid_transmitters) == 1:
        raise ValueError('Invalid Transmitter UUID: {0}'.format(invalid_transmitters[0]))

    raise ValueError('Invalid Transmitter UUIDs: {0}'.format(invalid_transmitters))
