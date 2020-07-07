"""SatNOGS Network django management command to set last seen value on stations entries"""
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from network.base.models import Station


class Command(BaseCommand):
    """Django management command to set last seen value on stations entries"""
    help = 'Updates Last_Seen Timestamp for given Stations'

    def add_arguments(self, parser):
        parser.add_argument('station_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for station_id in options['station_id']:
            try:
                ground_station = Station.objects.get(id=station_id)
            except Station.DoesNotExist:
                self.stderr.write('Station with ID {} does not exist'.format(station_id))
                return

            timestamp = now()
            ground_station.last_seen = timestamp
            ground_station.save()
            self.stdout.write(
                'Updated Last_Seen for Station {} to {}'.format(station_id, timestamp)
            )
