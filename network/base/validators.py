"""Django base validators for SatNOGS Network"""
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.timezone import make_aware, utc


class ObservationOverlapError(Exception):
    """Error when observation overlaps with already scheduled one"""


class OutOfRangeError(Exception):
    """Error when transmitter is our of station's antenna frequency range"""


class NegativeElevationError(Exception):
    """Error when satellite doesn't raise above station's horizon"""


class SinglePassError(Exception):
    """Error when between given start and end datetimes there are more than one satellite passes"""


class NoTleSetError(Exception):
    """Error when satellite doesn't have available TLE set"""


def check_start_datetime(start):
    """Validate start datetime"""
    if start < make_aware(datetime.now(), utc):
        raise ValueError("Start datetime should be in the future!")
    if start < make_aware(datetime.now() + timedelta(minutes=settings.OBSERVATION_DATE_MIN_START),
                          utc):
        raise ValueError(
            "Start datetime should be in the future, at least {0} minutes from now".format(
                settings.OBSERVATION_DATE_MIN_START
            )
        )


def check_end_datetime(end):
    """Validate end datetime"""
    if end < make_aware(datetime.now(), utc):
        raise ValueError("End datetime should be in the future!")
    max_duration = settings.OBSERVATION_DATE_MIN_START + settings.OBSERVATION_DATE_MAX_RANGE
    if end > make_aware(datetime.now() + timedelta(minutes=max_duration), utc):
        raise ValueError(
            "End datetime should be in the future, at most {0} minutes from now".
            format(max_duration)
        )


def check_start_end_datetimes(start, end):
    """Validate the pair of start and end datetimes"""
    if start > end:
        raise ValueError("End datetime should be after Start datetime!")
    if (end - start) < timedelta(seconds=settings.OBSERVATION_DURATION_MIN):
        raise ValueError(
            "Duration of observation should be at least {0} seconds".format(
                settings.OBSERVATION_DURATION_MIN
            )
        )


def downlink_low_is_in_range(antenna, transmitter):
    """Return true if transmitter frequency is in station's antenna frequency range"""
    if transmitter['downlink_low'] is not None:
        downlink_low = transmitter['downlink_low']
        for frequency_range in antenna.frequency_ranges.all():
            if frequency_range.min_frequency <= downlink_low <= frequency_range.max_frequency:
                return True
    return False


def is_transmitter_in_station_range(transmitter, station):
    """Return true if transmitter frequency is in one of the station's antennas frequency ranges"""
    for gs_antenna in station.antennas.all():
        if downlink_low_is_in_range(gs_antenna, transmitter):
            return True
    return False


def check_transmitter_station_pairs(transmitter_station_list):
    """Validate the pairs of transmitter and stations"""
    out_of_range_pairs = [
        (str(pair[0]['uuid']), int(pair[1].id)) for pair in transmitter_station_list
        if not is_transmitter_in_station_range(pair[0], pair[1])
    ]
    if out_of_range_pairs:
        if len(out_of_range_pairs) == 1:
            raise OutOfRangeError(
                'Transmitter out of station frequency range.'
                ' Transmitter-Station pair: {0}'.format(out_of_range_pairs[0])
            )
        raise OutOfRangeError(
            'Transmitter out of station frequency range. '
            'Transmitter-Station pairs: {0}'.format(out_of_range_pairs)
        )


def check_overlaps(stations_dict):
    """Check for overlaps among requested observations"""
    for station in stations_dict.keys():
        periods = stations_dict[station]
        total_periods = len(periods)
        for i in range(0, total_periods):
            start_i = periods[i][0]
            end_i = periods[i][1]
            for j in range(i + 1, total_periods):
                start_j = periods[j][0]
                end_j = periods[j][1]
                if ((start_j <= start_i <= end_j) or (start_j <= end_i <= end_j)
                        or (start_i <= start_j and end_i >= end_j)):  # noqa: W503
                    raise ObservationOverlapError(
                        'Observations of station {0} overlap'.format(station)
                    )
