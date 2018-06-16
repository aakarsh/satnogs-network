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


def calculate_polar_data(observer, satellite, start, end, points):
    observer = observer.copy()
    satellite = satellite.copy()
    duration = (start - end).total_seconds()
    delta = duration / points
    temp_date = start
    data = []
    while temp_date < end:
        observer.date = temp_date
        satellite.compute(observer)
        data.append([float(format(math.degrees(satellite.alt), '.4f')),
                     float(format(math.degrees(satellite.az), '.4f'))])
        temp_date = temp_date - timedelta(seconds=delta)
    temp_date = end
    observer.date = temp_date
    satellite.compute(observer)
    data.append([float(format(math.degrees(satellite.alt), '.4f')),
                 float(format(math.degrees(satellite.az), '.4f'))])
    return data


def resolve_overlaps(station, gs_data, start, end):
    overlapped = False
    if gs_data:
        for datum in gs_data:
            if datum.is_past:
                continue
            if datum.start <= end and start <= datum.end:
                overlapped = True
                if datum.start <= start and datum.end >= end:
                    return ()
                if start < datum.start and end > datum.end:
                    start1 = start
                    end1 = datum.start
                    start2 = datum.end
                    end2 = end
                    return start1, end1, start2, end2
                if datum.start <= start:
                    start = datum.end
                if datum.end >= end:
                    end = datum.start
    if overlapped:
        return start, end, overlapped
    else:
        return start, end


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
