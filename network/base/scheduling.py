import math
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now, make_aware, utc
from network.base.models import Satellite, Tle, Observation
from network.base.perms import schedule_station_perms
from network.base.validators import ObservationOverlapError

import ephem


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


def over_min_duration(duration):
    return duration > settings.OBSERVATION_DURATION_MIN


def max_elevation_in_window(observer, satellite, pass_tca, window_start, window_end):
    # In this case this is an overlapped observation
    # re-calculate elevation and start/end azimuth
    if window_start > pass_tca:
        # Observation window in the second half of the pass
        # Thus highest elevation right at the beginning of the window
        return get_elevation(observer, satellite, window_start)
    elif window_end < pass_tca:
        # Observation window in the first half of the pass
        # Thus highest elevation right at the end of the window
        return get_elevation(observer, satellite, window_end)
    else:
        return get_elevation(observer, satellite, pass_tca)


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
                    window1 = resolve_overlaps(scheduled_obs,
                                               start, datum.start - timedelta(seconds=30))
                    window2 = resolve_overlaps(scheduled_obs,
                                               datum.end + timedelta(seconds=30), end)
                    return (window1[0] + window2[0], True)
                if datum.start <= start:
                    start = datum.end + timedelta(seconds=30)
                if datum.end >= end:
                    end = datum.start - timedelta(seconds=30)
    return ([(start, end)], overlapped)


def create_station_window(window_start, window_end, azr, azs, elevation, tle,
                          valid_duration, overlapped, overlap_ratio=0):
    return {'start': window_start.strftime("%Y-%m-%d %H:%M:%S.%f"),
            'end': window_end.strftime("%Y-%m-%d %H:%M:%S.%f"),
            'az_start': azr,
            'az_end': azs,
            'elev_max': elevation,
            'tle0': tle.tle0,
            'tle1': tle.tle1,
            'tle2': tle.tle2,
            'valid_duration': valid_duration,
            'overlapped': overlapped,
            'overlap_ratio': overlap_ratio}


def create_station_windows(scheduled_obs, overlapped, pass_params, observer, satellite, tle):
    """
    This function takes a pre-calculated pass (described by pass_params) over a certain station
    and a list of already scheduled observations, and calculates observation windows during which
    the station is available to observe the pass.

    Returns the list of all available observation windows
    """
    station_windows = []

    windows, windows_changed = resolve_overlaps(scheduled_obs,
                                                pass_params['rise_time'],
                                                pass_params['set_time'])

    if len(windows) == 0:
        # No nonrlapping windows found
        return []
    if windows_changed:
        # Windows changed due to overlap, recalculate observation parameters
        if overlapped == 0:
            return []
        elif overlapped == 1:
            initial_duration = (pass_params['set_time'] - pass_params['rise_time']).total_seconds()
            for window_start, window_end in windows:
                elevation = max_elevation_in_window(observer, satellite,
                                                    pass_params['tca_time'],
                                                    window_start, window_end)
                window_duration = (window_end - window_start).total_seconds()
                if not over_min_duration(window_duration):
                    continue

                # Add a window for a partial pass
                station_windows.append(create_station_window(
                    window_start,
                    window_end,
                    get_azimuth(observer, satellite, window_start),
                    get_azimuth(observer, satellite, window_end),
                    elevation,
                    tle,
                    True,
                    True,
                    min(1, 1 - (window_duration / initial_duration))
                ))
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
            station_windows.append(create_station_window(
                pass_params['rise_time'],
                pass_params['set_time'],
                pass_params['rise_az'],
                pass_params['set_az'],
                pass_params['tca_alt'],
                tle,
                duration_validity,
                True,
                min(1, 1 - (window_duration / initial_duration))
            ))
    else:
        window_duration = (windows[0][1] - windows[0][0]).total_seconds()
        if over_min_duration(window_duration):
            # Add a window for a full pass
            station_windows.append(create_station_window(
                pass_params['rise_time'],
                pass_params['set_time'],
                pass_params['rise_az'],
                pass_params['set_az'],
                pass_params['tca_alt'],
                tle,
                True,
                False,
                0
            ))
    return station_windows


def next_pass(observer, satellite, issue105=False):
    tr, azr, tt, altt, ts, azs = observer.next_pass(satellite)
    # Convert output of pyephems.next_pass into processible values
    pass_start = make_aware(ephem.Date(tr).datetime(), utc)
    pass_end = make_aware(ephem.Date(ts).datetime(), utc)
    pass_tca = make_aware(ephem.Date(tt).datetime(), utc)
    pass_azr = float(format(math.degrees(azr), '.0f'))
    pass_azs = float(format(math.degrees(azs), '.0f'))
    pass_elevation = float(format(math.degrees(altt), '.0f'))

    if ephem.Date(tr).datetime() > ephem.Date(ts).datetime():
        # set time before rise time (bug in pyephem)
        # https://github.com/brandon-rhodes/pyephem/issues/105
        # move observer time after the current pass end
        time_start_new = pass_end + timedelta(minutes=1)
        observer.date = time_start_new.strftime("%Y-%m-%d %H:%M:%S.%f")
        if issue105:
            raise ValueError('Recursion of next_pass() due to\
                              https://github.com/brandon-rhodes/pyephem/issues/105')
        else:
            return next_pass(observer, satellite, True)

    return {'rise_time': pass_start,
            'set_time': pass_end,
            'tca_time': pass_tca,
            'rise_az': pass_azr,
            'set_az': pass_azs,
            'tca_alt': pass_elevation}


def predict_available_observation_windows(station, min_horizon, overlapped, tle,
                                          start, end, sat):
    '''Calculate available observation windows for a certain station and satellite during
    the given time period.

    :param station: Station for scheduling
    :type station: Station django.db.model.Model
    :param min_horizon: Overwrite station minimum horizon if defined
    :type min_horizon: integer or None
    :param overlapped: Calculate and return overlapped observations fully, truncated or not at all
    :type overlapped: integer values: 0 (no return), 1(truncated overlaps), 2(full overlaps)
    :param tle: Satellite current TLE
    :param tle: Satellite current TLE
    :type tle: Tle django.db.model.Model
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
    tle_as_str_array = tle.str_array
    # Initialize pyehem Satellite for propagation
    satellite = ephem.readtle(*tle_as_str_array)
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
        except ValueError:
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
        scheduled_obs = Observation.objects \
            .filter(ground_station=station) \
            .filter(end__gt=now())

        station_windows.extend(create_station_windows(scheduled_obs, overlapped, pass_params,
                                                      observer, satellite, tle))
    return passes_found, station_windows


def create_new_observation(station, transmitter, start, end, author):
    scheduled_obs = Observation.objects.filter(ground_station=station).filter(end__gt=now())
    window = resolve_overlaps(scheduled_obs, start, end)

    if window[1]:
        raise ObservationOverlapError(
            'One or more observations of station {0} overlap with the already scheduled ones.'
            .format(int(station.id)))

    sat = Satellite.objects.get(norad_cat_id=transmitter['norad_cat_id'])
    tle = Tle.objects.get(id=sat.latest_tle.id)

    sat_ephem = ephem.readtle(str(sat.latest_tle.tle0),
                              str(sat.latest_tle.tle1),
                              str(sat.latest_tle.tle2))
    observer = ephem.Observer()
    observer.lon = str(station.lng)
    observer.lat = str(station.lat)
    observer.elevation = station.alt

    mid_pass_time = start + (end - start) / 2

    rise_azimuth = get_azimuth(observer, sat_ephem, start)
    max_altitude = get_elevation(observer, sat_ephem, mid_pass_time)
    set_azimuth = get_azimuth(observer, sat_ephem, end)

    return Observation(
        satellite=sat, tle=tle, author=author, start=start, end=end,
        ground_station=station, rise_azimuth=rise_azimuth, max_altitude=max_altitude,
        set_azimuth=set_azimuth, transmitter_uuid=transmitter['uuid'],
        transmitter_description=transmitter['description'], transmitter_type=transmitter['type'],
        transmitter_uplink_low=transmitter['uplink_low'],
        transmitter_uplink_high=transmitter['uplink_high'],
        transmitter_uplink_drift=transmitter['uplink_drift'],
        transmitter_downlink_low=transmitter['downlink_low'],
        transmitter_downlink_high=transmitter['downlink_high'],
        transmitter_downlink_drift=transmitter['downlink_drift'],
        transmitter_mode=transmitter['mode'], transmitter_invert=transmitter['invert'],
        transmitter_baud=transmitter['baud'], transmitter_created=transmitter['updated']
    )


def get_available_stations(stations, downlink, user):
    available_stations = []
    for station in stations:
        if not schedule_station_perms(user, station):
            continue

        # Skip if this station is not capable of receiving the frequency
        if not downlink:
            continue
        frequency_supported = False
        for gs_antenna in station.antenna.all():
            if (gs_antenna.frequency <= downlink <= gs_antenna.frequency_max):
                frequency_supported = True
        if not frequency_supported:
            continue

        available_stations.append(station)
    return available_stations
