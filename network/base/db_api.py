import requests
from django.conf import settings

db_api_url = settings.DB_API_ENDPOINT


class DBConnectionError(Exception):
    pass


def transmitters_api_request(url):
    if not db_api_url:
        raise DBConnectionError('Error in DB API connection. Blank DB API URL!')
    try:
        request = requests.get(url)
    except requests.exceptions.RequestException:
        raise DBConnectionError('Error in DB API connection. Please try again!')
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


def get_transmitters_by_uuid_list(uuid_list):
    if not uuid_list:
        raise ValueError('Expected a non empty list of UUIDs.')
    if len(uuid_list) == 1:
        transmitter = get_transmitter_by_uuid(uuid_list[0])
        if not transmitter:
            raise ValueError('Invalid Transmitter UUID: {0}'.format(str(uuid_list[0])))
        return {transmitter[0]['uuid']: transmitter[0]}
    else:
        transmitters_list = get_transmitters()

        transmitters = {t['uuid']: t for t in transmitters_list if t['uuid'] in uuid_list}
        invalid_transmitters = [
            str(uuid) for uuid in set(uuid_list).difference(set(transmitters.keys()))
        ]
        if not invalid_transmitters:
            return transmitters
        else:
            if len(invalid_transmitters) == 1:
                raise ValueError('Invalid Transmitter UUID: {0}'.format(invalid_transmitters[0]))
            else:
                raise ValueError('Invalid Transmitter UUIDs: {0}'.format(invalid_transmitters))
