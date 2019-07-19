from django.core.cache import cache

from network.base.models import Observation


def transmitter_total_count(uuid):
    data = cache.get('tr-{0}-total-count'.format(uuid))
    if data is None:
        obs = Observation.objects.filter(transmitter_uuid=uuid)
        data = obs.exclude(vetted_status='failed').count()
        cache.set('tr-{0}-total-count'.format(uuid), data, 3600)
        return data
    return data


def transmitter_good_count(uuid):
    data = cache.get('tr-{0}-suc-count'.format(uuid))
    if data is None:
        obs = Observation.objects.filter(transmitter_uuid=uuid)
        data = obs.filter(vetted_status='good').count()
        cache.set('tr-{0}-suc-count'.format(uuid), data, 3600)
        return data
    return data


def transmitter_bad_count(uuid):
    data = cache.get('tr-{0}-bad-count'.format(uuid))
    if data is None:
        obs = Observation.objects.filter(transmitter_uuid=uuid)
        data = obs.filter(vetted_status='bad').count()
        cache.set('tr-{0}-bad-count'.format(uuid), data, 3600)
        return data
    return data


def transmitter_unvetted_count(uuid):
    data = cache.get('tr-{0}-unk-count'.format(uuid))
    if data is None:
        obs = Observation.objects.filter(transmitter_uuid=uuid)
        data = obs.filter(vetted_status='unknown').count()
        cache.set('tr-{0}-unk-count'.format(uuid), data, 3600)
        return data
    return data


def transmitter_stats_by_uuid(uuid):
    total_count = transmitter_total_count(uuid)
    unvetted_count = transmitter_unvetted_count(uuid)
    good_count = transmitter_good_count(uuid)
    bad_count = transmitter_bad_count(uuid)
    unvetted_rate = 0
    success_rate = 0
    bad_rate = 0

    if total_count:
        unvetted_rate = int(100 * (float(unvetted_count) / float(total_count)))
        success_rate = int(100 * (float(good_count) / float(total_count)))
        bad_rate = int(100 * (float(bad_count) / float(total_count)))

    return {
        'total_count': total_count,
        'unvetted_count': unvetted_count,
        'good_count': good_count,
        'bad_count': bad_count,
        'unvetted_rate': unvetted_rate,
        'success_rate': success_rate,
        'bad_rate': bad_rate
    }


def satellite_stats_by_transmitter_list(transmitter_list):
    total_count = 0
    unvetted_count = 0
    good_count = 0
    bad_count = 0
    unvetted_rate = 0
    success_rate = 0
    bad_rate = 0
    for transmitter in transmitter_list:
        transmitter_stats = transmitter_stats_by_uuid(transmitter['uuid'])
        total_count += transmitter_stats['total_count']
        unvetted_count += transmitter_stats['unvetted_count']
        good_count += transmitter_stats['good_count']
        bad_count += transmitter_stats['bad_count']

    if total_count:
        unvetted_rate = int(100 * (float(unvetted_count) / float(total_count)))
        success_rate = int(100 * (float(good_count) / float(total_count)))
        bad_rate = int(100 * (float(bad_count) / float(total_count)))

    return {
        'total_count': total_count,
        'unvetted_count': unvetted_count,
        'good_count': good_count,
        'bad_count': bad_count,
        'unvetted_rate': unvetted_rate,
        'success_rate': success_rate,
        'bad_rate': bad_rate
    }
