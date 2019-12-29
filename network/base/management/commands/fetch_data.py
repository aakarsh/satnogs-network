"""SatNOGS Network django management command to fetch data (Satellites and Transmitters)"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from network.base.models import Satellite, Transmitter


class Command(BaseCommand):
    """Django management command to fetch Satellites and Transmitters from SatNOGS DB"""
    help = 'Fetches Satellites and Transmitters from SaTNOGS DB'

    def handle(self, *args, **options):
        db_api_url = settings.DB_API_ENDPOINT
        if not db_api_url:
            self.stdout.write("Zero length api url, fetching is stopped")
            return
        satellites_url = "{}satellites".format(db_api_url)
        transmitters_url = "{}transmitters".format(db_api_url)

        try:
            self.stdout.write("Fetching Satellites from {}".format(satellites_url))
            r_satellites = requests.get(satellites_url)

            self.stdout.write("Fetching Transmitters from {}".format(transmitters_url))
            r_transmitters = requests.get(transmitters_url)
        except requests.exceptions.ConnectionError:
            raise CommandError('API is unreachable')

        # Fetch Satellites
        satellites_added = 0
        satellites_updated = 0
        for satellite in r_satellites.json():
            norad_cat_id = satellite['norad_cat_id']
            satellite.pop('decayed', None)
            try:
                # Update Satellite
                existing_satellite = Satellite.objects.get(norad_cat_id=norad_cat_id)
                existing_satellite.__dict__.update(satellite)
                existing_satellite.save()
                satellites_updated += 1
            except Satellite.DoesNotExist:
                # Add Satellite
                satellite.pop('telemetries', None)
                Satellite.objects.create(**satellite)
                satellites_added += 1

        self.stdout.write(
            'Added/Updated {}/{} satellites from db.'.format(satellites_added, satellites_updated)
        )

        # Fetch Transmitters
        transmitters_added = 0
        transmitters_skipped = 0
        for transmitter in r_transmitters.json():
            uuid = transmitter['uuid']

            try:
                # Transmitter already exists, skip
                Transmitter.objects.get(uuid=uuid)
                transmitters_skipped += 1
            except Transmitter.DoesNotExist:
                # Create Transmitter
                Transmitter.objects.create(uuid=uuid)
                transmitters_added += 1

        self.stdout.write(
            'Added/Skipped {}/{} transmitters from db.'.format(
                transmitters_added, transmitters_skipped
            )
        )
