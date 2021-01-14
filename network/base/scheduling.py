"""SatNOGS Network scheduling functions"""
# ephem is missing lon, lat, elevation and horizon attributes in Observer class slots,
# Disable assigning-non-slot pylint error:
# pylint: disable=E0237
import json
import math
from datetime import timedelta

import ephem
from django.conf import settings
from django.utils.timezone import make_aware, now, utc

from network.base.db_api import DBConnectionError, get_tle_set_by_norad_id
from network.base.models import Observation, Satellite
from network.base.perms import schedule_stations_perms
from network.base.validators import NegativeElevationError, NoTleSetError, \
    ObservationOverlapError, SinglePassError


def get_altitude(observer, satellite, date):
    """Returns altitude of satellite in a specific date for a specific observer"""
    observer = observer.copy()
    satellite = satellite.copy()
    observer.date = date
    satellite.compute(observer)
    return float(format(math.degrees(satellite.alt), '.0f'))


def get_azimuth(observer, satellite, date):
    """Returns azimuth of satellite in a specific date for a specific observer"""
    observer = observer.copy()
    satellite = satellite.copy()
    observer.date = date
    satellite.compute(observer)
    return float(format(math.degrees(satellite.az), '.0f'))


def over_min_duration(duration):
    """Returns if duration is bigger than the minimum one set in settings"""
    return duration > settings.OBSERVATION_DURATION_MIN


def max_altitude_in_window(observer, satellite, pass_tca, window_start, window_end):
    """Finds the maximum altitude of a satellite during a certain observation window"""
    # In this case this is an overlapped observation
    # re-calculate altitude and start/end azimuth
    if window_start > pass_tca:
        # Observation window in the second half of the pass
        # Thus highest altitude right at the beginning of the window
        return get_altitude(observer, satellite, window_start)
    if window_end < pass_tca:
        # Observation window in the first half of the pass
        # Thus highest altitude right at the end of the window
        return get_altitude(observer, satellite, window_end)
    return get_altitude(observer, satellite, pass_tca)


def resolve_overlaps(scheduled_obs, start, end):
    """
    This function checks for overlaps between all existing observations on `scheduled_obs`
    and a potential new observation with given `start` and `end` time.

    Returns
    - ([], True)                                  if total overlap exists
    - ([(start1, end1), (start2, end2)], True)    if the overlap happens in the middle
                                                  of the new observation
    - ([(start, end)], True)                      if the overlap happens at one end
                                                  of the new observation
    - ([(start, end)], False)                     if no overlap exists
    """
    overlapped = False
    if scheduled_obs:
        for datum in scheduled_obs:
            if datum.start <= end and start <= datum.end:
                overlapped = True
                if datum.start <= start and datum.end >= end:
                    return ([], True)
                if start < datum.start and end > datum.end:
                    # In case of splitting the window  to two we
                    # check for overlaps for each generated window.
                    window1 = resolve_overlaps(
                        scheduled_obs, start, datum.start - timedelta(seconds=30)
                    )
                    window2 = resolve_overlaps(
                        scheduled_obs, datum.end + timedelta(seconds=30), end
                    )
                    return (window1[0] + window2[0], True)
                if datum.start <= start:
                    start = datum.end + timedelta(seconds=30)
                if datum.end >= end:
                    end = datum.start - timedelta(seconds=30)
    return ([(start, end)], overlapped)


def create_station_window(
    window_start,
    window_end,
    azr,
    azs,
    altitude,
    tle,
    valid_duration,
    overlapped,
    overlap_ratio=0
):
    """Creates an observation window"""
    return {
        'start': window_start.strftime("%Y-%m-%d %H:%M:%S.%f"),
        'end': window_end.strftime("%Y-%m-%d %H:%M:%S.%f"),
        'az_start': azr,
        'az_end': azs,
        'elev_max': altitude,
        'tle0': tle['tle0'],
        'tle1': tle['tle1'],
        'tle2': tle['tle2'],
        'valid_duration': valid_duration,
        'overlapped': overlapped,
        'overlap_ratio': overlap_ratio
    }


def create_station_windows(scheduled_obs, overlapped, pass_params, observer, satellite, tle):
    """
    This function takes a pre-calculated pass (described by pass_params) over a certain station
    and a list of already scheduled observations, and calculates observation windows during which
    the station is available to observe the pass.

    Returns the list of all available observation windows
    """
    station_windows = []

    windows, windows_changed = resolve_overlaps(
        scheduled_obs, pass_params['rise_time'], pass_params['set_time']
    )

    if not windows:
        # No overlapping windows found
        return []
    if windows_changed:
        # Windows changed due to overlap, recalculate observation parameters
        if overlapped == 0:
            return []

        if overlapped == 1:
            initial_duration = (pass_params['set_time'] - pass_params['rise_time']).total_seconds()
            for window_start, window_end in windows:
                altitude = max_altitude_in_window(
                    observer, satellite, pass_params['tca_time'], window_start, window_end
                )
                window_duration = (window_end - window_start).total_seconds()
                if not over_min_duration(window_duration):
                    continue

                # Add a window for a partial pass
                station_windows.append(
                    create_station_window(
                        window_start, window_end, get_azimuth(observer, satellite, window_start),
                        get_azimuth(observer, satellite, window_end), altitude, tle, True, True,
                        min(1, 1 - (window_duration / initial_duration))
                    )
                )
        elif overlapped == 2:
            initial_duration = (pass_params['set_time'] - pass_params['rise_time']).total_seconds()
            total_window_duration = 0
            window_duration = 0
            duration_validity = True
            for window_start, window_end in windows:
                window_duration = (window_end - window_start).total_seconds()
                duration_validity = duration_validity and over_min_duration(window_duration)
                total_window_duration += window_duration

            # Add a window for the overlapped pass
            station_windows.append(
                create_station_window(
                    pass_params['rise_time'], pass_params['set_time'], pass_params['rise_az'],
                    pass_params['set_az'], pass_params['tca_alt'], tle, duration_validity, True,
                    min(1, 1 - (window_duration / initial_duration))
                )
            )
    else:
        window_duration = (windows[0][1] - windows[0][0]).total_seconds()
        if over_min_duration(window_duration):
            # Add a window for a full pass
            station_windows.append(
                create_station_window(
                    pass_params['rise_time'], pass_params['set_time'], pass_params['rise_az'],
                    pass_params['set_az'], pass_params['tca_alt'], tle, True, False, 0
                )
            )
    return station_windows


def next_pass(observer, satellite, singlepass=True):
    """Returns the next pass of the satellite above the observer"""
    rise_time, rise_az, tca_time, tca_alt, set_time, set_az = observer.next_pass(
        satellite, singlepass
    )
    # Convert output of pyephems.next_pass into processible values
    pass_start = make_aware(ephem.Date(rise_time).datetime(), utc)
    pass_end = make_aware(ephem.Date(set_time).datetime(), utc)
    pass_tca = make_aware(ephem.Date(tca_time).datetime(), utc)
    pass_azr = float(format(math.degrees(rise_az), '.0f'))
    pass_azs = float(format(math.degrees(set_az), '.0f'))
    pass_altitude = float(format(math.degrees(tca_alt), '.0f'))

    return {
        'rise_time': pass_start,
        'set_time': pass_end,
        'tca_time': pass_tca,
        'rise_az': pass_azr,
        'set_az': pass_azs,
        'tca_alt': pass_altitude
    }


def predict_available_observation_windows(station, min_horizon, overlapped, tle, start, end):
    '''Calculate available observation windows for a certain station and satellite during
    the given time period.

    :param station: Station for scheduling
    :type station: Station django.db.model.Model
    :param min_horizon: Overwrite station minimum horizon if defined
    :type min_horizon: integer or None
    :param overlapped: Calculate and return overlapped observations fully, truncated or not at all
    :type overlapped: integer values: 0 (no return), 1(truncated overlaps), 2(full overlaps)
    :param tle: Satellite current TLE
    :type tle: dictionary with Tle details
    :param start: Start datetime of scheduling period
    :type start: datetime string in '%Y-%m-%d %H:%M'
    :param end: End datetime of scheduling period
    :type end: datetime string in '%Y-%m-%d %H:%M'
    :param sat: Satellite for scheduling
    :type sat: Satellite django.db.model.Model

    :return: List of passes found and list of available observation windows
    '''
    passes_found = []
    station_windows = []
    # Initialize pyehem Satellite for propagation
    satellite = ephem.readtle(str(tle['tle0']), str(tle['tle1']), str(tle['tle2']))
    # Initialize pyephem Observer for propagation
    observer = ephem.Observer()
    observer.lon = str(station.lng)
    observer.lat = str(station.lat)
    observer.elevation = station.alt
    observer.date = ephem.Date(start)
    if min_horizon is not None:
        observer.horizon = str(min_horizon)
    else:
        observer.horizon = str(station.horizon)

    try:
        satellite.compute(observer)
    except ValueError:
        return passes_found, station_windows

    while True:
        try:
            pass_params = next_pass(observer, satellite)
        # We catch TypeError, to avoid cases like this one that is described in ephem issue:
        # https://github.com/brandon-rhodes/pyephem/issues/176
        except (TypeError, ValueError):
            break

        # no match if the sat will not rise above the configured min horizon
        if pass_params['rise_time'] >= end:
            # start of next pass outside of window bounds
            break

        if pass_params['set_time'] > end:
            # end of next pass outside of window bounds
            break

        passes_found.append(pass_params)

        time_start_new = pass_params['set_time'] + timedelta(minutes=1)
        observer.date = time_start_new.strftime("%Y-%m-%d %H:%M:%S.%f")

        window_duration = (pass_params['set_time'] - pass_params['rise_time']).total_seconds()
        if not over_min_duration(window_duration):
            continue

        # Check if overlaps with existing scheduled observations
        # Adjust or discard window if overlaps exist
        scheduled_obs = station.scheduled_obs

        station_windows.extend(
            create_station_windows(
                scheduled_obs, overlapped, pass_params, observer, satellite, tle
            )
        )
    return passes_found, station_windows


def create_new_observation(station, transmitter, start, end, author, tle_set=None):
    """
    Creates and returns a new Observation object

    Arguments:
    station - network.base.models.Station
    transmitter - network.base.models.Transmitter
    start - datetime
    end - datetime
    author - network.base.models.User
    tle_set - empty list or list of one tle set

    Returns network.base.models.Observation
    Raises NegativeElevationError, ObservationOverlapError, SinglePassError or more
    """
    scheduled_obs = Observation.objects.filter(ground_station=station).filter(end__gt=now())
    window = resolve_overlaps(scheduled_obs, start, end)

    if window[1]:
        raise ObservationOverlapError(
            'One or more observations of station {0} overlap with the already scheduled ones.'.
            format(station.id)
        )

    sat = Satellite.objects.get(norad_cat_id=transmitter['norad_cat_id'])
    if not tle_set:
        try:
            tle_set = get_tle_set_by_norad_id(transmitter['norad_cat_id'])
        except DBConnectionError:
            tle_set = []

        if not tle_set:
            raise NoTleSetError(
                'Satellite with transmitter {} and NORAD ID {} hasn\'t available TLE set'.format(
                    transmitter['uuid'], transmitter['norad_cat_id']
                )
            )

    tle = tle_set[0]
    sat_ephem = ephem.readtle(str(tle['tle0']), str(tle['tle1']), str(tle['tle2']))
    observer = ephem.Observer()
    observer.lon = str(station.lng)
    observer.lat = str(station.lat)
    observer.elevation = station.alt

    mid_pass_time = start + (end - start) / 2

    rise_azimuth = get_azimuth(observer, sat_ephem, start)
    rise_altitude = get_altitude(observer, sat_ephem, start)
    max_altitude = get_altitude(observer, sat_ephem, mid_pass_time)
    set_azimuth = get_azimuth(observer, sat_ephem, end)
    set_altitude = get_altitude(observer, sat_ephem, end)

    if rise_altitude < 0:
        raise NegativeElevationError(
            "Satellite with transmitter {} has negative altitude ({})"
            " for station {} at start datetime: {}".format(
                transmitter['uuid'], rise_altitude, station.id, start
            )
        )
    if set_altitude < 0:
        raise NegativeElevationError(
            "Satellite with transmitter {} has negative altitude ({})"
            " for station {} at end datetime: {}".format(
                transmitter['uuid'], set_altitude, station.id, end
            )
        )
    # Using a short time (1min later) after start for finding the next pass of the satellite to
    # check that end datetime is before the start datetime of the next pass, in other words that
    # end time belongs to the same single pass.
    observer.date = start + timedelta(minutes=1)
    next_satellite_pass = next_pass(observer, sat_ephem, False)
    if next_satellite_pass['rise_time'] < end:
        raise SinglePassError(
            "Observation should include only one pass of the satellite with transmitter {}"
            " on station {}, please check start({}) and end({}) datetimes and try again".format(
                transmitter['uuid'], station.id, start, end
            )
        )

    # List all station antennas with their frequency ranges.
    antennas = []
    for antenna in station.antennas.all().prefetch_related('frequency_ranges', 'antenna_type'):
        ranges = []
        for frequency_range in antenna.frequency_ranges.all():
            ranges.append(
                {
                    "min": frequency_range.min_frequency,
                    "max": frequency_range.max_frequency
                }
            )
        antennas.append({"type": antenna.antenna_type.name, "ranges": ranges})

    return Observation(
        satellite=sat,
        tle_line_0=tle['tle0'],
        tle_line_1=tle['tle1'],
        tle_line_2=tle['tle2'],
        tle_source=tle['tle_source'],
        tle_updated=tle['updated'],
        author=author,
        start=start,
        end=end,
        ground_station=station,
        testing=station.testing,
        rise_azimuth=rise_azimuth,
        max_altitude=max_altitude,
        set_azimuth=set_azimuth,
        transmitter_uuid=transmitter['uuid'],
        transmitter_description=transmitter['description'],
        transmitter_type=transmitter['type'],
        transmitter_uplink_low=transmitter['uplink_low'],
        transmitter_uplink_high=transmitter['uplink_high'],
        transmitter_uplink_drift=transmitter['uplink_drift'],
        transmitter_downlink_low=transmitter['downlink_low'],
        transmitter_downlink_high=transmitter['downlink_high'],
        transmitter_downlink_drift=transmitter['downlink_drift'],
        transmitter_mode=transmitter['mode'],
        transmitter_invert=transmitter['invert'],
        transmitter_baud=transmitter['baud'],
        transmitter_created=transmitter['updated'],
        station_alt=station.alt,
        station_lat=station.lat,
        station_lng=station.lng,
        station_antennas=json.dumps(antennas)
    )


def get_available_stations(stations, downlink, user):
    """Returns stations for scheduling filtered by a specific downlink and user's permissions"""
    available_stations = []
    stations_perms = schedule_stations_perms(user, stations)
    stations_with_permissions = [station for station in stations if stations_perms[station.id]]
    for station in stations_with_permissions:
        # Skip if this station is not capable of receiving the frequency
        if not downlink:
            continue
        for gs_antenna in station.antennas.all():
            for frequency_range in gs_antenna.frequency_ranges.all():
                if frequency_range.min_frequency <= downlink <= frequency_range.max_frequency:
                    available_stations.append(station)
                    break
            else:
                continue  # to the next antenna of the station
            break  # station added to the available stations

    return available_stations
