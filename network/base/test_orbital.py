"""Orbital class for generating valid TLE sets for specific location and time"""
import math

import ephem

PARAMETERS = {
    'name': 'FAKESAT-1',
    'catalog_num': '00000',
    'classifier': 'U',
    'cospar_id': '00000A',
    'mean_motion_first': '.00000000',
    'mean_motion_second': '00000-0',
    'drag_term': '50000-4',
    'set_number': '0',
    'inclination': '90.0000',
    'eccentricity': '0001000',
    'argument_perigee': '000.0000',
    'mean_motion': '15.50000000',
    'revolutions': '0'
}


def calculate_checksum(line):
    "Calculate checksum of a given TLE set line"
    line_sum = 0
    for line_char in line:
        if line_char.isdigit():
            line_sum += int(line_char)
        if line_char == '-':
            line_sum += 1
    return line_sum % 10


def datetime_to_epoch(date):
    "Return epoch from a given datetime"
    timetuple = date.timetuple()

    minutes = timetuple.tm_min + timetuple.tm_sec / 60
    hours = timetuple.tm_hour + minutes / 60
    days = timetuple.tm_yday + hours / 24
    year = timetuple.tm_year

    return year, days


def generate_fake_tle(latitude, longitude, elevation, date):
    "Generate fake TLE using a location and a date"
    tle = []

    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.elevation = int(elevation)
    observer.date = date

    # Calculate RAAN and mean anomaly
    right_ascension = (observer.sidereal_time() * 180 / math.pi) % 360
    mean_anomaly = (observer.lat * 180 / math.pi) % 360

    epoch_year, epoch_day = datetime_to_epoch(date)

    # Assemble lines
    tle.append(PARAMETERS['name'].ljust(69))
    tle.append(
        '1 {:5.5}{:.1} {:8.8} {:.2}{:012.8f} {:>10.10} {:>8.8} {:>8.8} 0 {:>4.4}'.format(
            PARAMETERS['catalog_num'],
            PARAMETERS['classifier'],
            PARAMETERS['cospar_id'],
            str(epoch_year),
            epoch_day,
            PARAMETERS['mean_motion_first'],
            PARAMETERS['mean_motion_second'],
            PARAMETERS['drag_term'],
            PARAMETERS['set_number'],
        )
    )
    tle.append(
        '2 {:>5.5} {:>8.8} {:>8.4f} {:>7.7} {:>8.8} {:>8.4f} {:>11.11}{:>5.5}'.format(
            PARAMETERS['catalog_num'],
            PARAMETERS['inclination'],
            right_ascension,
            PARAMETERS['eccentricity'],
            PARAMETERS['argument_perigee'],
            mean_anomaly,
            PARAMETERS['mean_motion'],
            PARAMETERS['revolutions'],
        )
    )

    # Calculate checksums
    tle[1] += str(calculate_checksum(tle[1]))
    tle[2] += str(calculate_checksum(tle[2]))

    return tle
