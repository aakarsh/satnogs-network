from django.core.exceptions import ObjectDoesNotExist


def schedule_perms(user):
    """
    This context flag will determine if user can schedule an observation.
    That includes station owners, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if user.is_authenticated():
        # User has online station (status=2)
        if user.ground_stations.filter(status=2).exists():
            return True
        # User has testing station (status=1)
        if user.ground_stations.filter(status=1).exists():
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
    if user.is_authenticated():
        # User has online station (status=2) and station is online
        try:
            if user.ground_stations.filter(status=2).exists() and station.status == 2:
                return True
        except (AttributeError, ObjectDoesNotExist):
            pass
        # If the station is testing (status=1) and user is its owner
        try:
            if station.status == 1 and station.owner == user:
                return True
        except (AttributeError, ObjectDoesNotExist):
            pass
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True

    return False


def delete_perms(user, observation):
    """
    This context flag will determine if a delete button appears for the observation.
    That includes observer, station owner involved, moderators, admins.
    see: https://wiki.satnogs.org/Operation#Network_permissions_matrix
    """
    if not observation.is_started and user.is_authenticated():
        # User owns the observation
        try:
            if observation.author == user:
                return True
        except AttributeError:
            pass
        # User owns the station
        try:
            if observation.ground_station.owner == user:
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
    if user.is_authenticated():
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
            if observation.ground_station.owner == user:
                return True
        except AttributeError:
            pass
        # User has special permissions
        if user.groups.filter(name='Moderators').exists():
            return True
        if user.is_superuser:
            return True
    return False
