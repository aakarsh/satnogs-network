"""SatNOGS Network django management command to initialize a new database"""
from __future__ import absolute_import

from django.core.management import call_command
from django.core.management.base import BaseCommand

from network.base.models import Antenna
from network.base.tests import DemodDataFactory, RealisticObservationFactory, \
    StationFactory, generate_payload, generate_payload_name


class Command(BaseCommand):
    """Django management command to initialize a new database"""
    help = 'Create initial fixtures'

    def handle(self, *args, **options):
        station_fixture_count = 40
        observation_fixture_count = 200
        demoddata_fixture_count = 40

        # Migrate
        self.stdout.write("Creating database...")
        call_command('migrate')

        #  Initial data
        call_command('loaddata', 'antennas')
        call_command('fetch_data')

        # Update TLEs
        call_command('update_all_tle')

        # Create random fixtures for remaining models
        self.stdout.write("Creating fixtures...")
        StationFactory.create_batch(
            station_fixture_count, antennas=(Antenna.objects.all().values_list('id', flat=True))
        )
        self.stdout.write("Added {} stations.".format(station_fixture_count))
        RealisticObservationFactory.create_batch(observation_fixture_count)
        self.stdout.write("Added {} observations.".format(observation_fixture_count))
        for _ in range(demoddata_fixture_count):
            DemodDataFactory.create(
                payload_demod__data=generate_payload(),
                payload_demod__filename=generate_payload_name()
            )
        self.stdout.write("Added {} DemodData objects.".format(demoddata_fixture_count))

        # Create superuser
        self.stdout.write("Creating a superuser...")
        call_command('createsuperuser')
