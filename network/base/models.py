import os
from datetime import datetime, timedelta
from PIL import Image
import requests
from shortuuidfield import ShortUUIDField
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.db import models
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import now

from network.users.models import User
from network.base.managers import ObservationManager
from rest_framework.authtoken.models import Token

ANTENNA_BANDS = ['HF', 'VHF', 'UHF', 'L', 'S', 'C', 'X', 'KU']
ANTENNA_TYPES = (
    ('dipole', 'Dipole'),
    ('v-dipole', 'V-Dipole'),
    ('discone', 'Discone'),
    ('ground', 'Ground Plane'),
    ('yagi', 'Yagi'),
    ('cross-yagi', 'Cross Yagi'),
    ('helical', 'Helical'),
    ('parabolic', 'Parabolic'),
    ('vertical', 'Vertical'),
    ('turnstile', 'Turnstile'),
    ('quadrafilar', 'Quadrafilar'),
    ('eggbeater', 'Eggbeater'),
    ('lindenblad', 'Lindenblad'),
    ('paralindy', 'Parasitic Lindenblad'),
    ('patch', 'Patch')
)
OBSERVATION_STATUSES = (
    ('unknown', 'Unknown'),
    ('good', 'Good'),
    ('bad', 'Bad'),
    ('failed', 'Failed'),
)
STATION_STATUSES = (
    (2, 'Online'),
    (1, 'Testing'),
    (0, 'Offline'),
)
SATELLITE_STATUS = ['alive', 'dead', 're-entered']
TRANSMITTER_STATUS = ['active', 'inactive', 'invalid']
TRANSMITTER_TYPE = ['Transmitter', 'Transceiver', 'Transponder']


def _name_obs_files(instance, filename):
    return 'data_obs/{0}/{1}'.format(instance.id, filename)


def _name_obs_demoddata(instance, filename):
    # On change of the string bellow, change it also at api/views.py
    return 'data_obs/{0}/{1}'.format(instance.observation.id, filename)


def _observation_post_save(sender, instance, created, **kwargs):
    """
    Post save Observation operations
    * Auto vet as good obserfvation with Demod Data
    * Mark Observations from testing stations
    * Update client version for ground station
    """
    post_save.disconnect(_observation_post_save, sender=Observation)
    if created and instance.ground_station.testing:
        instance.testing = True
        instance.save()
    if instance.has_demoddata and instance.vetted_status == 'unknown':
        instance.vetted_status = 'good'
        instance.vetted_datetime = now()
        instance.save()
    post_save.connect(_observation_post_save, sender=Observation)


def _station_post_save(sender, instance, created, **kwargs):
    """
    Post save Station operations
    * Store current status
    """
    post_save.disconnect(_station_post_save, sender=Station)
    if not created:
        current_status = instance.status
        if instance.is_offline:
            instance.status = 0
        elif instance.testing:
            instance.status = 1
        else:
            instance.status = 2
        instance.save()
        if instance.status != current_status:
            StationStatusLog.objects.create(station=instance, status=instance.status)
    else:
        StationStatusLog.objects.create(station=instance, status=instance.status)
    post_save.connect(_station_post_save, sender=Station)


def _tle_post_save(sender, instance, created, **kwargs):
    """
    Post save Tle operations
    * Update TLE for future observations
    """
    if created:
        start_time = now() + timedelta(minutes=10)
        Observation.objects.filter(satellite=instance.satellite, start__gt=start_time) \
                           .update(tle=instance.id)


def validate_image(fieldfile_obj):
    filesize = fieldfile_obj.file.size
    megabyte_limit = 2.0
    if filesize > megabyte_limit * 1024 * 1024:
        raise ValidationError("Max file size is %sMB" % str(megabyte_limit))


class Antenna(models.Model):
    """Model for antennas tracked with SatNOGS."""
    frequency = models.PositiveIntegerField()
    frequency_max = models.PositiveIntegerField()
    band = models.CharField(choices=zip(ANTENNA_BANDS, ANTENNA_BANDS),
                            max_length=5)
    antenna_type = models.CharField(choices=ANTENNA_TYPES, max_length=15)

    def __unicode__(self):
        return '{0} - {1} - {2} - {3}'.format(self.band, self.antenna_type,
                                              self.frequency,
                                              self.frequency_max)


class Station(models.Model):
    """Model for SatNOGS ground stations."""
    owner = models.ForeignKey(User, related_name="ground_stations",
                              on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=45)
    image = models.ImageField(upload_to='ground_stations', blank=True,
                              validators=[validate_image])
    alt = models.PositiveIntegerField(help_text='In meters above sea level')
    lat = models.FloatField(validators=[MaxValueValidator(90), MinValueValidator(-90)],
                            help_text='eg. 38.01697')
    lng = models.FloatField(validators=[MaxValueValidator(180), MinValueValidator(-180)],
                            help_text='eg. 23.7314')
    qthlocator = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    antenna = models.ManyToManyField(Antenna, blank=True, related_name="stations",
                                     help_text=('If you want to add a new Antenna contact '
                                                '<a href="https://community.satnogs.org/" '
                                                'target="_blank">SatNOGS Team</a>'))
    featured_date = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    testing = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=STATION_STATUSES, default=0)
    horizon = models.PositiveIntegerField(help_text='In degrees above 0', default=10)
    description = models.TextField(max_length=500, blank=True, help_text='Max 500 characters')
    client_version = models.CharField(max_length=45, blank=True)
    target_utilization = models.IntegerField(validators=[MaxValueValidator(100),
                                                         MinValueValidator(0)],
                                             help_text='Target utilization factor for '
                                                       'your station',
                                             null=True, blank=True)

    class Meta:
        ordering = ['-status']

    def get_image(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        else:
            return settings.STATION_DEFAULT_IMAGE

    @property
    def is_online(self):
        try:
            heartbeat = self.last_seen + timedelta(minutes=int(settings.STATION_HEARTBEAT_TIME))
            return heartbeat > now()
        except TypeError:
            return False

    @property
    def is_offline(self):
        return not self.is_online

    @property
    def is_testing(self):
        if self.is_online:
            if self.status == 1:
                return True
        return False

    def state(self):
        if not self.status:
            return format_html('<span style="color:red;">Offline</span>')
        if self.status == 1:
            return format_html('<span style="color:orange;">Testing</span>')
        return format_html('<span style="color:green">Online</span>')

    @property
    def success_rate(self):
        rate = cache.get('station-{0}-rate'.format(self.id))
        if not rate:
            observations = self.observations.exclude(testing=True).exclude(vetted_status="unknown")
            success = observations.filter(id__in=(o.id for o in observations
                                                  if o.is_good or o.is_bad)).count()
            if observations:
                rate = int(100 * (float(success) / float(observations.count())))
                cache.set('station-{0}-rate'.format(self.id), rate)
            else:
                rate = False
        return rate

    @property
    def observations_count(self):
        count = self.observations.all().count()
        return count

    @property
    def observations_future_count(self):
        count = self.observations.is_future().count()
        return count

    @property
    def apikey(self):
        try:
            token = Token.objects.get(user=self.owner)
        except Token.DoesNotExist:
            token = Token.objects.create(user=self.owner)
        return token

    def __unicode__(self):
        return "%d - %s" % (self.pk, self.name)


post_save.connect(_station_post_save, sender=Station)


class StationStatusLog(models.Model):
    station = models.ForeignKey(Station, related_name='station_logs',
                                on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(choices=STATION_STATUSES, default=0)
    changed = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed']

    def __unicode__(self):
        return '{0} - {1}'.format(self.station, self.status)


class Satellite(models.Model):
    """Model for SatNOGS satellites."""
    norad_cat_id = models.PositiveIntegerField()
    norad_follow_id = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=45)
    names = models.TextField(blank=True)
    image = models.CharField(max_length=100, blank=True, null=True)
    manual_tle = models.BooleanField(default=False)
    status = models.CharField(choices=zip(SATELLITE_STATUS, SATELLITE_STATUS),
                              max_length=10, default='alive')

    class Meta:
        ordering = ['norad_cat_id']

    def get_image(self):
        if self.image:
            return self.image
        else:
            return settings.SATELLITE_DEFAULT_IMAGE

    @property
    def latest_tle(self):
        try:
            latest_tle = Tle.objects.filter(satellite=self).latest('updated')
            return latest_tle
        except Tle.DoesNotExist:
            return False

    @property
    def tle_no(self):
        try:
            line = self.latest_tle.tle1
            return line[64:68]
        except AttributeError:
            return False

    @property
    def tle_epoch(self):
        try:
            line = self.latest_tle.tle1
        except AttributeError:
            return False
        yd, s = line[18:32].split('.')
        epoch = (datetime.strptime(yd, "%y%j") +
                 timedelta(seconds=float("." + s) * 24 * 60 * 60))
        return epoch

    @property
    def data_count(self):
        return Observation.objects.filter(satellite=self).exclude(vetted_status='failed').count()

    @property
    def good_count(self):
        data = Observation.objects.filter(satellite=self)
        return data.filter(vetted_status='good').count()

    @property
    def bad_count(self):
        data = Observation.objects.filter(satellite=self)
        return data.filter(vetted_status='bad').count()

    @property
    def unvetted_count(self):
        data = Observation.objects.filter(satellite=self)
        return data.filter(vetted_status='unknown',
                           end__lte=now()).count()

    @property
    def future_count(self):
        data = Observation.objects.filter(satellite=self)
        return data.filter(end__gt=now()).count()

    @property
    def success_rate(self):
        try:
            return int(100 * (float(self.good_count) / float(self.data_count)))
        except (ZeroDivisionError, TypeError):
            return 0

    @property
    def bad_rate(self):
        try:
            return int(100 * (float(self.bad_count) / float(self.data_count)))
        except (ZeroDivisionError, TypeError):
            return 0

    @property
    def unvetted_rate(self):
        try:
            return int(100 * (float(self.unvetted_count) / float(self.data_count)))
        except (ZeroDivisionError, TypeError):
            return 0

    def __unicode__(self):
        return self.name


class Tle(models.Model):
    tle0 = models.CharField(max_length=100, blank=True)
    tle1 = models.CharField(max_length=200, blank=True)
    tle2 = models.CharField(max_length=200, blank=True)
    updated = models.DateTimeField(auto_now=True, blank=True)
    satellite = models.ForeignKey(Satellite, related_name='tles',
                                  on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['tle0']

    def __unicode__(self):
        uni_name = "%d - %s" % (self.id, self.tle0)
        return uni_name

    @property
    def str_array(self):
        # tle fields are unicode, pyephem and others expect python strings
        return [str(self.tle0), str(self.tle1), str(self.tle2)]


post_save.connect(_tle_post_save, sender=Tle)


class Transmitter(models.Model):
    """Model for antennas transponders."""
    uuid = ShortUUIDField(db_index=True)
    sync_to_db = models.BooleanField(default=False)


class Observation(models.Model):
    """Model for SatNOGS observations."""
    satellite = models.ForeignKey(Satellite, related_name='observations',
                                  on_delete=models.SET_NULL, null=True, blank=True)
    tle = models.ForeignKey(Tle, related_name='observations',
                            on_delete=models.SET_NULL, null=True, blank=True)
    author = models.ForeignKey(User, related_name='observations',
                               on_delete=models.SET_NULL, null=True, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    ground_station = models.ForeignKey(Station, related_name='observations',
                                       on_delete=models.SET_NULL, null=True, blank=True)
    client_version = models.CharField(max_length=255, blank=True)
    client_metadata = models.TextField(blank=True)
    payload = models.FileField(upload_to=_name_obs_files, blank=True, null=True)
    waterfall = models.ImageField(upload_to=_name_obs_files, blank=True, null=True)
    vetted_datetime = models.DateTimeField(null=True, blank=True)
    vetted_user = models.ForeignKey(User, related_name='observations_vetted',
                                    on_delete=models.SET_NULL, null=True, blank=True)
    vetted_status = models.CharField(choices=OBSERVATION_STATUSES,
                                     max_length=20, default='unknown')
    testing = models.BooleanField(default=False)
    rise_azimuth = models.FloatField(blank=True, null=True)
    max_altitude = models.FloatField(blank=True, null=True)
    set_azimuth = models.FloatField(blank=True, null=True)
    archived = models.BooleanField(default=False)
    archive_identifier = models.CharField(max_length=255, blank=True)
    archive_url = models.URLField(blank=True, null=True)
    transmitter_uuid = ShortUUIDField(db_index=True)
    transmitter_description = models.TextField(default='')
    transmitter_type = models.CharField(choices=zip(TRANSMITTER_TYPE, TRANSMITTER_TYPE),
                                        max_length=11, default='Transmitter')
    transmitter_uplink_low = models.BigIntegerField(blank=True, null=True)
    transmitter_uplink_high = models.BigIntegerField(blank=True, null=True)
    transmitter_uplink_drift = models.IntegerField(blank=True, null=True)
    transmitter_downlink_low = models.BigIntegerField(blank=True, null=True)
    transmitter_downlink_high = models.BigIntegerField(blank=True, null=True)
    transmitter_downlink_drift = models.IntegerField(blank=True, null=True)
    transmitter_mode = models.CharField(max_length=10, blank=True, null=True)
    transmitter_invert = models.BooleanField(default=False)
    transmitter_baud = models.FloatField(validators=[MinValueValidator(0)], blank=True, null=True)
    transmitter_created = models.DateTimeField(default=now)

    objects = ObservationManager.as_manager()

    @property
    def is_past(self):
        return self.end < now()

    @property
    def is_future(self):
        return self.end > now()

    @property
    def is_started(self):
        return self.start < now()

    # this payload has been vetted good/bad/failed by someone
    @property
    def is_vetted(self):
        return not self.vetted_status == 'unknown'

    # this payload has been vetted as good by someone
    @property
    def is_good(self):
        return self.vetted_status == 'good'

    # this payload has been vetted as bad by someone
    @property
    def is_bad(self):
        return self.vetted_status == 'bad'

    # this payload has been vetted as failed by someone
    @property
    def is_failed(self):
        return self.vetted_status == 'failed'

    @property
    def has_waterfall(self):
        """Run some checks on the waterfall for existence of data."""
        if self.waterfall is None:
            return False
        if not os.path.isfile(os.path.join(settings.MEDIA_ROOT, self.waterfall.name)):
            return False
        if self.waterfall.size == 0:
            return False
        return True

    @property
    def has_audio(self):
        """Run some checks on the payload for existence of data."""
        if self.archive_url:
            return True
        if self.payload is None:
            return False
        if not os.path.isfile(os.path.join(settings.MEDIA_ROOT, self.payload.name)):
            return False
        if self.payload.size == 0:
            return False
        return True

    @property
    def has_demoddata(self):
        """Check if the observation has Demod Data."""
        if self.demoddata.count():
            return True
        return False

    @property
    def audio_url(self):
        if self.has_audio:
            if self.archive_url:
                r = requests.get(self.archive_url, allow_redirects=False)
                try:
                    url = r.headers['Location']
                    return url
                except Exception:
                    logger = logging.getLogger(__name__)
                    logger.warning("Request to '%s' returned status code: %s",
                                   r.url, r.status_code)
                    return ''
            else:
                return self.payload.url
        return ''

    class Meta:
        ordering = ['-start', '-end']

    def __unicode__(self):
        return str(self.id)

    def get_absolute_url(self):
        return reverse('base:observation_view', kwargs={'id': self.id})


@receiver(models.signals.post_delete, sender=Observation)
def observation_remove_files(sender, instance, **kwargs):
    if instance.payload:
        if os.path.isfile(instance.payload.path):
            os.remove(instance.payload.path)
    if instance.waterfall:
        if os.path.isfile(instance.waterfall.path):
            os.remove(instance.waterfall.path)


post_save.connect(_observation_post_save, sender=Observation)


class DemodData(models.Model):
    observation = models.ForeignKey(Observation, related_name='demoddata',
                                    on_delete=models.CASCADE)
    payload_demod = models.FileField(upload_to=_name_obs_demoddata, unique=True)
    copied_to_db = models.BooleanField(default=False)

    def is_image(self):
        with open(self.payload_demod.path) as fp:
            try:
                Image.open(fp)
            except (IOError, TypeError):
                return False
            else:
                return True

    def display_payload(self):
        with open(self.payload_demod.path) as fp:
            payload = fp.read()
            try:
                return unicode(payload)
            except UnicodeDecodeError:
                data = payload.encode('hex').upper()
                return ' '.join(data[i:i + 2] for i in xrange(0, len(data), 2))


@receiver(models.signals.post_delete, sender=DemodData)
def demoddata_remove_files(sender, instance, **kwargs):
    if instance.payload_demod:
        if os.path.isfile(instance.payload_demod.path):
            os.remove(instance.payload_demod.path)
