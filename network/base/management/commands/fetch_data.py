import requests

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from network.base.models import Mode, Satellite, Transmitter


class Command(BaseCommand):
    help = 'Fetch Modes, Satellites and Transmitters from satnogs-db'

    def handle(self, *args, **options):
        db_api_url = settings.DB_API_ENDPOINT
        if len(db_api_url) == 0:
            self.stdout.write("Zero length api url, fetching is stopped")
            return
        mode_url = '{}modes'.format(db_api_url)
        satellites_url = "{}satellites".format(db_api_url)
        transmitters_url = "{}transmitters".format(db_api_url)

        try:
            self.stdout.write("Fetching Modes from {}".format(mode_url))
            r_modes = requests.get(mode_url)

            self.stdout.write("Fetching Satellites from {}".format(satellites_url))
            r_satellites = requests.get(satellites_url)

            self.stdout.write("Fetching Transmitters from {}".format(transmitters_url))
            r_transmitters = requests.get(transmitters_url)
        except requests.exceptions.ConnectionError:
            raise CommandError('API is unreachable')

        # Fetch Modes
        for mode in r_modes.json():
            id = mode['id']
            name = mode['name']
            try:
                existing_mode = Mode.objects.get(id=id)
                existing_mode.__dict__.update(mode)
                existing_mode.save()
                self.stdout.write('Mode {0} updated'.format(name))
            except Mode.DoesNotExist:
                Mode.objects.create(**mode)
                self.stdout.write('Mode {0} added'.format(name))

        # Fetch Satellites
        for satellite in r_satellites.json():
            norad_cat_id = satellite['norad_cat_id']
            name = satellite['name']
            satellite.pop('decayed', None)
            try:
                existing_satellite = Satellite.objects.get(norad_cat_id=norad_cat_id)
                existing_satellite.__dict__.update(satellite)
                existing_satellite.save()
                self.stdout.write('Satellite {0}-{1} updated'.format(norad_cat_id, name))
            except Satellite.DoesNotExist:
                Satellite.objects.create(**satellite)
                self.stdout.write('Satellite {0}-{1} added'.format(norad_cat_id, name))

        # Fetch Transmitters
        for transmitter in r_transmitters.json():
            norad_cat_id = transmitter['norad_cat_id']
            uuid = transmitter['uuid']
            description = transmitter['description']
            mode_id = transmitter['mode_id']

            try:
                sat = Satellite.objects.get(norad_cat_id=norad_cat_id)
            except Satellite.DoesNotExist:
                self.stdout.write('Satellite {0} not present'.format(norad_cat_id))
            transmitter.pop('norad_cat_id')

            try:
                mode = Mode.objects.get(id=mode_id)
            except Mode.DoesNotExist:
                mode = None
            try:
                existing_transmitter = Transmitter.objects.get(uuid=uuid)
                existing_transmitter.__dict__.update(transmitter)
                existing_transmitter.satellite = sat
                existing_transmitter.save()
                self.stdout.write('Transmitter {0}-{1} updated'.format(uuid, description))
            except Transmitter.DoesNotExist:
                new_transmitter = Transmitter.objects.create(**transmitter)
                new_transmitter.satellite = sat
                new_transmitter.mode = mode
                new_transmitter.save()
                self.stdout.write('Transmitter {0}-{1} created'.format(uuid, description))
