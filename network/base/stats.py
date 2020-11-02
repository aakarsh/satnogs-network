"""Module for calculating and keep in cache satellite and transmitter statistics"""
import math

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils.timezone import now

from network.base.models import Observation


def transmitter_stats_by_uuid(uuid):
    """Calculate and put in cache transmitter statistics"""
    stats = cache.get('tr-{0}-stats'.format(uuid))
    if stats is None:
        stats = Observation.objects.filter(transmitter_uuid=uuid).exclude(
            status__lt=-100
        ).aggregate(
            future=Count('pk', filter=Q(end__gt=now())),
            bad=Count('pk', filter=Q(status__range=(-100, -1))),
            unknown=Count('pk', filter=Q(status__range=(0, 99), end__lte=now())),
            good=Count('pk', filter=Q(status__gte=100)),
        )
        cache.set('tr-{0}-stats'.format(uuid), stats, 3600)
    total_count = 0
    unknown_count = 0 if stats['unknown'] is None else stats['unknown']
    future_count = 0 if stats['future'] is None else stats['future']
    good_count = 0 if stats['good'] is None else stats['good']
    bad_count = 0 if stats['bad'] is None else stats['bad']
    total_count = unknown_count + future_count + good_count + bad_count
    unknown_rate = 0
    future_rate = 0
    success_rate = 0
    bad_rate = 0

    if total_count:
        unknown_rate = math.trunc(10000 * (unknown_count / total_count)) / 100
        future_rate = math.trunc(10000 * (future_count / total_count)) / 100
        success_rate = math.trunc(10000 * (good_count / total_count)) / 100
        bad_rate = math.trunc(10000 * (bad_count / total_count)) / 100

    return {
        'total_count': total_count,
        'unknown_count': unknown_count,
        'future_count': future_count,
        'good_count': good_count,
        'bad_count': bad_count,
        'unknown_rate': unknown_rate,
        'future_rate': future_rate,
        'success_rate': success_rate,
        'bad_rate': bad_rate
    }


def satellite_stats_by_transmitter_list(transmitter_list):
    """Calculate satellite statistics"""
    total_count = 0
    unknown_count = 0
    future_count = 0
    good_count = 0
    bad_count = 0
    unknown_rate = 0
    future_rate = 0
    success_rate = 0
    bad_rate = 0
    for transmitter in transmitter_list:
        transmitter_stats = transmitter_stats_by_uuid(transmitter['uuid'])
        total_count += transmitter_stats['total_count']
        unknown_count += transmitter_stats['unknown_count']
        future_count += transmitter_stats['future_count']
        good_count += transmitter_stats['good_count']
        bad_count += transmitter_stats['bad_count']

    if total_count:
        unknown_rate = math.trunc(10000 * (unknown_count / total_count)) / 100
        future_rate = math.trunc(10000 * (future_count / total_count)) / 100
        success_rate = math.trunc(10000 * (good_count / total_count)) / 100
        bad_rate = math.trunc(10000 * (bad_count / total_count)) / 100

    return {
        'total_count': total_count,
        'unknown_count': unknown_count,
        'future_count': future_count,
        'good_count': good_count,
        'bad_count': bad_count,
        'unknown_rate': unknown_rate,
        'future_rate': future_rate,
        'success_rate': success_rate,
        'bad_rate': bad_rate
    }


def transmitters_with_stats(transmitters_list):
    """Returns a list of transmitters with their statistics"""
    transmitters_with_stats_list = []
    for transmitter in transmitters_list:
        transmitter_stats = transmitter_stats_by_uuid(transmitter['uuid'])
        transmitter_with_stats = dict(transmitter, **transmitter_stats)
        transmitters_with_stats_list.append(transmitter_with_stats)
    return transmitters_with_stats_list


def unknown_observations_count(user):
    """Returns a count of unknown status observations per user"""
    user_unknown_count = cache.get('user-{0}-unknown-count'.format(user.id))
    if user_unknown_count is None:
        user_unknown_count = Observation.objects.filter(
            author=user, status__range=(0, 99), end__lte=now()
        ).exclude(waterfall='').count()
        cache.set('user-{0}-unknown-count'.format(user.id), user_unknown_count, 120)

    return user_unknown_count
