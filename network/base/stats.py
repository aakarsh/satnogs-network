from django.core.cache import cache

from network.base.models import Observation


def transmitter_total_count(uuid):
    return Observation.objects.filter(transmitter_uuid=uuid) \
                              .exclude(vetted_status='failed') \
                              .count()


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


def transmitter_success_rate(uuid):
    rate = cache.get('tr-{0}-suc-rate'.format(uuid))
    if rate is None:
        try:
            ratio = float(transmitter_good_count(uuid)) / float(transmitter_total_count(uuid))
            rate = int(100 * ratio)
            cache.set('tr-{0}-suc-rate'.format(uuid), rate, 3600)
            return rate
        except (ZeroDivisionError, TypeError):
            cache.set('tr-{0}-suc-rate'.format(uuid), 0, 3600)
            return 0
    return rate


def transmitter_bad_rate(uuid):
    rate = cache.get('tr-{0}-bad-rate'.format(uuid))
    if rate is None:
        try:
            ratio = float(transmitter_bad_count(uuid)) / float(transmitter_total_count(uuid))
            rate = int(100 * ratio)
            cache.set('tr-{0}-bad-rate'.format(uuid), rate, 3600)
            return rate
        except (ZeroDivisionError, TypeError):
            cache.set('tr-{0}-bad-rate'.format(uuid), 0, 3600)
            return 0
    return rate


def transmitter_unvetted_rate(uuid):
    rate = cache.get('tr-{0}-unk-rate'.format(uuid))
    if rate is None:
        try:
            ratio = float(transmitter_unvetted_count(uuid)) / float(transmitter_total_count(uuid))
            rate = int(100 * ratio)
            cache.set('tr-{0}-unk-rate'.format(uuid), rate, 3600)
            return rate
        except (ZeroDivisionError, TypeError):
            cache.set('tr-{0}-unk-rate'.format(uuid), 0, 3600)
            return 0
    return rate


def transmitter_stats_by_uuid(uuid):
    return {
        'total_count': transmitter_total_count(uuid),
        'unvetted_count': transmitter_unvetted_count(uuid),
        'good_count': transmitter_good_count(uuid),
        'bad_count': transmitter_bad_count(uuid),
        'success_rate': transmitter_success_rate(uuid),
        'bad_rate': transmitter_bad_rate(uuid),
        'unvetted_rate': transmitter_unvetted_rate(uuid)
    }
