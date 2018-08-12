from django.core.management.base import BaseCommand
from django.core.management import call_command

from network.base.models import Antenna
from network.base.tests import (generate_payload, generate_payload_name,
                                DemodDataFactory, StationFactory, ObservationFactory)


class Command(BaseCommand):
    help = 'Create initial fixtures'

    def handle(self, *args, **options):
        # Migrate
        self.stdout.write("Creating database...")
        call_command('migrate')

        #  Initial data
        call_command('loaddata', 'antennas')
        call_command('fetch_data')

        # Create random fixtures for remaining models
        self.stdout.write("Creating fixtures...")
        StationFactory.create_batch(40,
                                    antennas=(Antenna.objects.all().values_list('id', flat=True)))
        ObservationFactory.create_batch(200)
        for _ in range(40):
            DemodDataFactory.create(payload_demod__data=generate_payload(),
                                    payload_demod__filename=generate_payload_name())

        # Update TLEs
        call_command('update_all_tle')

        # Create superuser
        self.stdout.write("Creating a superuser...")
        call_command('createsuperuser')
