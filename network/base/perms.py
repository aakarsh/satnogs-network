"""SatNOGS Network base permissions"""
from django.core.exceptions import ObjectDoesNotExist


class UserNoPermissionError(Exception):
    """Error when user has not persmission"""


def schedule_perms(user):
    """
    This context flag will determine if user can schedule an observation.
    That includes station owners, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if user.is_authenticated:
        stations_statuses = user.ground_stations.values_list('status', flat=True)
        # User has online station (status=2)
        if 2 in stations_statuses:
            return True
        # User has testing station (status=1)
        if 1 in stations_statuses:
            return True
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True

    return False


def schedule_station_perms(user, station):
    """
    This context flag will determine if user can schedule an observation.
    That includes station owners, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if user.is_authenticated:
        # User has online station (status=2) and station is online
        try:
            if user.ground_stations.filter(status=2).exists() and station.status == 2:
                return True
        except ObjectDoesNotExist:
            pass
        # If the station is testing (status=1) and user is its owner
        if station.status == 1 and station.owner == user:
            return True
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True

    return False


def schedule_stations_perms(user, stations):
    """
    This context flag will determine if user can schedule an observation.
    That includes station owners, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if user.is_authenticated:
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return {station.id: True for station in stations}
        if user.is_superuser:
            return {station.id: True for station in stations}
        # User has online station (status=2) and station is online
        try:
            if user.ground_stations.filter(status=2).exists():
                return {
                    s.id: s.status == 2 or (s.owner == user and s.status == 1)
                    for s in stations
                }

        except ObjectDoesNotExist:
            pass
        # If the station is testing (status=1) and user is its owner
        return {station.id: station.owner == user and station.status == 1 for station in stations}

    return {station.id: False for station in stations}


def check_schedule_perms_per_station(user, station_list):
    """Checks if user has permissions to schedule on stations"""
    stations_perms = schedule_stations_perms(user, station_list)
    stations_without_permissions = [
        int(station_id) for station_id in stations_perms.keys() if not stations_perms[station_id]
    ]
    if stations_without_permissions:
        if len(stations_without_permissions) == 1:
            raise UserNoPermissionError(
                'No permission to schedule observations on station: {0}'.format(
                    stations_without_permissions[0]
                )
            )
        raise UserNoPermissionError(
            'No permission to schedule observations on stations: {0}'.
            format(stations_without_permissions)
        )


def delete_perms(user, observation):
    """
    This context flag will determine if a delete button appears for the observation.
    That includes observer, station owner involved, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if not observation.is_started and user.is_authenticated:
        # User owns the observation
        try:
            if observation.author == user:
                return True
        except AttributeError:
            pass
        # User owns the station
        try:
            if observation.ground_station and observation.ground_station.owner == user:
                return True
        except (AttributeError, ObjectDoesNotExist):
            pass
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True
    return False


def vet_perms(user, observation):
    """
    This context flag will determine if vet buttons appears for the observation.
    That includes observer, station owner involved, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if user.is_authenticated:
        # User has online station (status=2)
        if user.ground_stations.filter(status=2).exists():
            return True
        # User owns the observation
        try:
            if observation.author == user:
                return True
        except AttributeError:
            pass
        # User owns the station
        try:
            if observation.ground_station and observation.ground_station.owner == user:
                return True
        except AttributeError:
            pass
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True
    return False


def modify_delete_station_perms(user, station):
    """
    This context flag will determine if the user can modify or delete a station
    or bulk-delete future observations on a station.
    That includes station owners, moderators and admins.
    """
    if user.is_authenticated:
        # User owns the station
        try:
            if user == station.owner:
                return True
        except AttributeError:
            pass
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True
    return False
