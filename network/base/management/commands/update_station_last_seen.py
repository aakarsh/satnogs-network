from django.core.management.base import LabelCommand
from django.utils.timezone import now

from network.base.models import Station


class Command(LabelCommand):
    args = '<Station IDs>'
    help = 'Updates Last_Seen Timestamp for given Stations'

    def handle_label(self, label, **options):
        try:
            gs = Station.objects.get(id=label)
        except Station.DoesNotExist:
            self.stderr.write('Station with ID {} does not exist'.format(label))
            return

        timestamp = now()
        gs.last_seen = timestamp
        gs.save()
        self.stdout.write('Updated Last_Seen for Station {} to {}'.format(label, timestamp))
