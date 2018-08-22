import math
from datetime import timedelta

from rest_framework.authtoken.models import Token

from django.core.cache import cache


def get_apikey(user):
    try:
        token = Token.objects.get(user=user)
    except Token.DoesNotExist:
        token = Token.objects.create(user=user)
    return token


def get_elevation(observer, satellite, date):
    observer = observer.copy()
    satellite = satellite.copy()
    observer.date = date
    satellite.compute(observer)
    return float(format(math.degrees(satellite.alt), '.0f'))


def get_azimuth(observer, satellite, date):
    observer = observer.copy()
    satellite = satellite.copy()
    observer.date = date
    satellite.compute(observer)
    return float(format(math.degrees(satellite.az), '.0f'))


def resolve_overlaps(station, gs_data, start, end):
    """
    This function checks for overlaps between all existing observations on `gs_data` and a
    potential new observation with given `start` and `end` time.

    Returns
    - ([], True)                                  if total overlap exists
    - ([(start1, end1), (start2, end2)], True)    if the overlap happens in the middle
                                                  of the new observation
    - ([(start, end)], True)                      if the overlap happens at one end
                                                  of the new observation
    - ([(start, end)], False)                     if no overlap exists
    """
    overlapped = False
    if gs_data:
        for datum in gs_data:
            if datum.start <= end and start <= datum.end:
                overlapped = True
                if datum.start <= start and datum.end >= end:
                    return ([], True)
                if start < datum.start and end > datum.end:
                    # In case of splitting the window  to two we
                    # check for overlaps for each generated window.
                    window1 = resolve_overlaps(station, gs_data,
                                               start, datum.start - timedelta(seconds=10))
                    window2 = resolve_overlaps(station, gs_data,
                                               datum.end + timedelta(seconds=10), end)
                    return (window1[0] + window2[0], True)
                if datum.start <= start:
                    start = datum.end + timedelta(seconds=10)
                if datum.end >= end:
                    end = datum.start - timedelta(seconds=10)
    return ([(start, end)], overlapped)


def cache_get_key(*args, **kwargs):
    import hashlib
    serialise = []
    for arg in args:
        serialise.append(str(arg))
    for key, arg in kwargs.items():
        serialise.append(str(key))
    serialise.append(str(arg))
    key = hashlib.md5("".join(serialise)).hexdigest()
    return key


def cache_for(time):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            key = cache_get_key(fn.__name__, *args, **kwargs)
            result = cache.get(key)
            if not result:
                result = fn(*args, **kwargs)
                cache.set(key, result, time)
            return result
        return wrapper
    return decorator
