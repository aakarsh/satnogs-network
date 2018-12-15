import math
from datetime import timedelta

from django.utils.timezone import now, make_aware, utc
from network.base.models import Satellite, Station, Tle, Transmitter, Observation

import ephem


class ObservationOverlapError(Exception):
    pass


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
                                               start, datum.start - timedelta(seconds=30))
                    window2 = resolve_overlaps(station, gs_data,
                                               datum.end + timedelta(seconds=30), end)
                    return (window1[0] + window2[0], True)
                if datum.start <= start:
                    start = datum.end + timedelta(seconds=30)
                if datum.end >= end:
                    end = datum.start - timedelta(seconds=30)
    return ([(start, end)], overlapped)


def create_station_window(window_start, window_end, overlapped,
                          azr, azs, elevation,
                          tle):
    return {'start': window_start.strftime("%Y-%m-%d %H:%M:%S.%f"),
            'end': window_end.strftime("%Y-%m-%d %H:%M:%S.%f"),
            'az_start': azr,
            'az_end': azs,
            'elev_max': elevation,
            'tle0': tle.tle0,
            'tle1': tle.tle1,
            'tle2': tle.tle2,
            'overlapped': overlapped}


def create_station_windows(station, existing_observations,
                           pass_params, observer, satellite, tle):
    station_windows = []

    windows, windows_changed = resolve_overlaps(station, existing_observations,
                                                pass_params['rise_time'],
                                                pass_params['set_time'])

    if len(windows) == 0:
        # No non-overlapping windows found
        return []

    if windows_changed:
        # Windows changed due to overlap, recalculate observation parameters
        for window_start, window_end in windows:
            elevation = max_elevation_in_window(observer, satellite,
                                                pass_params['tca_time'],
                                                window_start, window_end)
            if elevation < station.horizon:
                continue

            # Add a window for a partial pass
            station_windows.append(create_station_window(
                window_start, window_end, False,
                get_azimuth(observer, satellite, window_start),
                get_azimuth(observer, satellite, window_end),
                elevation,
                tle
            ))
    else:
        # Add a window for a full pass
        station_windows.append(create_station_window(
            pass_params['rise_time'],
            pass_params['set_time'],
            False,
            pass_params['rise_az'],
            pass_params['set_az'],
            pass_params['tca_alt'],
            tle
        ))
    return station_windows


def next_pass(observer, satellite):
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
        raise ValueError

    return {'rise_time': pass_start,
            'set_time': pass_end,
            'tca_time': pass_tca,
            'rise_az': pass_azr,
            'set_az': pass_azs,
            'tca_alt': pass_elevation}


def create_new_observation(station_id,
                           sat_id,
                           trans_id,
                           start_time,
                           end_time,
                           author):
    ground_station = Station.objects.get(id=station_id)
    gs_data = Observation.objects.filter(ground_station=ground_station).filter(end__gt=now())
    window = resolve_overlaps(ground_station, gs_data, start_time, end_time)

    if window[1]:
        raise ObservationOverlapError

    sat = Satellite.objects.get(norad_cat_id=sat_id)
    trans = Transmitter.objects.get(uuid=trans_id)
    tle = Tle.objects.get(id=sat.latest_tle.id)

    sat_ephem = ephem.readtle(str(sat.latest_tle.tle0),
                              str(sat.latest_tle.tle1),
                              str(sat.latest_tle.tle2))
    observer = ephem.Observer()
    observer.lon = str(ground_station.lng)
    observer.lat = str(ground_station.lat)
    observer.elevation = ground_station.alt

    mid_pass_time = start_time + (end_time - start_time) / 2

    rise_azimuth = get_azimuth(observer, sat_ephem, start_time)
    max_altitude = get_elevation(observer, sat_ephem, mid_pass_time)
    set_azimuth = get_azimuth(observer, sat_ephem, end_time)

    return Observation(satellite=sat, transmitter=trans, tle=tle, author=author,
                       start=start_time, end=end_time,
                       ground_station=ground_station,
                       rise_azimuth=rise_azimuth,
                       max_altitude=max_altitude,
                       set_azimuth=set_azimuth)
