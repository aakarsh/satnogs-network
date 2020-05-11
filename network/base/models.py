"""Django database base model for SatNOGS Network"""
from __future__ import absolute_import, division

import codecs
import logging
import os
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import OuterRef, Subquery
from django.dispatch import receiver
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import format_html
from django.utils.timezone import now
from PIL import Image
from rest_framework.authtoken.models import Token
from shortuuidfield import ShortUUIDField

from network.base.managers import ObservationManager
from network.base.utils import bands_from_range
from network.users.models import User

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


def _decode_pretty_hex(binary_data):
    """Return the binary data as hex dump of the following form: `DE AD C0 DE`"""

    data = codecs.encode(binary_data, 'hex').decode('ascii').upper()
    return ' '.join(data[i:i + 2] for i in range(0, len(data), 2))


def _name_obs_files(instance, filename):
    """Return a filepath formatted by Observation ID"""
    return 'data_obs/{0}/{1}'.format(instance.id, filename)


def _name_obs_demoddata(instance, filename):
    """Return a filepath for DemodData formatted by Observation ID"""
    # On change of the string bellow, change it also at api/views.py
    return 'data_obs/{0}/{1}'.format(instance.observation.id, filename)


def validate_image(fieldfile_obj):
    """Validates image size"""
    filesize = fieldfile_obj.file.size
    megabyte_limit = 2.0
    if filesize > megabyte_limit * 1024 * 1024:
        raise ValidationError("Max file size is %sMB" % str(megabyte_limit))


@python_2_unicode_compatible
class Station(models.Model):
    """Model for SatNOGS ground stations."""
    owner = models.ForeignKey(
        User, related_name="ground_stations", on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=45)
    image = models.ImageField(upload_to='ground_stations', blank=True, validators=[validate_image])
    alt = models.PositiveIntegerField(help_text='In meters above sea level')
    lat = models.FloatField(
        validators=[MaxValueValidator(90), MinValueValidator(-90)], help_text='eg. 38.01697'
    )
    lng = models.FloatField(
        validators=[MaxValueValidator(180), MinValueValidator(-180)], help_text='eg. 23.7314'
    )
    # https://en.wikipedia.org/wiki/Maidenhead_Locator_System
    qthlocator = models.CharField(max_length=8, blank=True)
    featured_date = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    testing = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=STATION_STATUSES, default=0)
    horizon = models.PositiveIntegerField(help_text='In degrees above 0', default=10)
    description = models.TextField(max_length=500, blank=True, help_text='Max 500 characters')
    client_version = models.CharField(max_length=45, blank=True)
    target_utilization = models.IntegerField(
        validators=[MaxValueValidator(100), MinValueValidator(0)],
        help_text='Target utilization factor for '
        'your station',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-status']
        indexes = [models.Index(fields=['-status', 'id'])]

    def get_image(self):
        """Return the image of the station or the default image if there is a defined one"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return settings.STATION_DEFAULT_IMAGE

    @property
    def is_online(self):
        """Return true if station is online"""
        try:
            heartbeat = self.last_seen + timedelta(minutes=int(settings.STATION_HEARTBEAT_TIME))
            return heartbeat > now()
        except TypeError:
            return False

    @property
    def is_offline(self):
        """Return true if station is offline"""
        return not self.is_online

    @property
    def is_testing(self):
        """Return true if station is online and in testing mode"""
        if self.is_online:
            if self.status == 1:
                return True
        return False

    def state(self):
        """Return the station status in html format"""
        if not self.status:
            return format_html('<span style="color:red;">Offline</span>')
        if self.status == 1:
            return format_html('<span style="color:orange;">Testing</span>')
        return format_html('<span style="color:green">Online</span>')

    @property
    def success_rate(self):
        """Return the success rate of the station - successful observation over failed ones"""
        rate = cache.get('station-{0}-rate'.format(self.id))
        if not rate:
            observations = self.observations.exclude(testing=True).exclude(vetted_status="unknown")
            success = observations.filter(
                id__in=(o.id for o in observations if o.is_good or o.is_bad)
            ).count()
            if observations:
                rate = int(100 * (float(success) / float(observations.count())))
                cache.set('station-{0}-rate'.format(self.id), rate)
            else:
                rate = False
        return rate

    @property
    def apikey(self):
        """Return station owner API key"""
        try:
            token = Token.objects.get(user=self.owner)
        except Token.DoesNotExist:
            token = Token.objects.create(user=self.owner)
        return token

    def __str__(self):
        if self.pk:
            return "%d - %s" % (self.pk, self.name)
        return "%s" % (self.name)

    def clean(self):
        if re.search('[^\x20-\x7E\xA0-\xFF]', self.name, re.IGNORECASE):
            raise ValidationError(
                {
                    'name': (
                        'Please use characters that belong to ISO-8859-1'
                        ' (https://en.wikipedia.org/wiki/ISO/IEC_8859-1).'
                    )
                }
            )
        if re.search('[^\n\r\t\x20-\x7E\xA0-\xFF]', self.description, re.IGNORECASE):
            raise ValidationError(
                {
                    'description': (
                        'Please use characters that belong to ISO-8859-1'
                        ' (https://en.wikipedia.org/wiki/ISO/IEC_8859-1).'
                    )
                }
            )


@python_2_unicode_compatible
class AntennaType(models.Model):
    """Model for antenna types."""
    name = models.CharField(max_length=25, unique=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Antenna(models.Model):
    """Model for antennas of SatNOGS ground stations."""
    antenna_type = models.ForeignKey(
        AntennaType, on_delete=models.PROTECT, related_name='antennas'
    )
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='antennas')

    @property
    def bands(self):
        """Return comma separated string of the bands that the antenna works on"""
        bands = []
        for frequency_range in self.frequency_ranges.all():
            for band in bands_from_range(frequency_range.min_frequency,
                                         frequency_range.max_frequency):
                if band not in bands:
                    bands.append(band)
        return ', '.join(bands)

    def __str__(self):
        if self.pk:
            return "%d - %s (#%s)" % (self.pk, self.antenna_type.name, self.station.id)
        if self.station.id:
            return "%s (#%s)" % (self.antenna_type.name, self.station.id)
        return "%s" % (self.antenna_type.name)


@python_2_unicode_compatible
class FrequencyRange(models.Model):
    """Model for frequency ranges of antennas."""
    antenna = models.ForeignKey(Antenna, on_delete=models.CASCADE, related_name='frequency_ranges')
    min_frequency = models.BigIntegerField()
    max_frequency = models.BigIntegerField()

    @property
    def bands(self):
        """Return comma separated string of the bands that of the frequeny range"""
        bands = bands_from_range(self.min_frequency, self.max_frequency)
        return ', '.join(bands)

    class Meta:
        ordering = ['min_frequency']

    def clean(self):
        if self.max_frequency < self.min_frequency:
            raise ValidationError(
                {
                    'min_frequency': (
                        'Minimum frequency is greater than the maximum one ({0} > {1}).'.format(
                            self.min_frequency, self.max_frequency
                        )
                    ),
                    'max_frequency': (
                        'Maximum frequency is less than the minimum one ({0} < {1}).'.format(
                            self.max_frequency, self.min_frequency
                        )
                    ),
                }
            )
        if self.min_frequency < settings.MIN_FREQUENCY_FOR_RANGE:
            raise ValidationError(
                {
                    'min_frequency': ('Minimum frequency should be less than {0}.').format(
                        settings.MIN_FREQUENCY_FOR_RANGE
                    )
                }
            )
        if self.max_frequency > settings.MAX_FREQUENCY_FOR_RANGE:
            raise ValidationError(
                {
                    'max_frequency': ('Maximum frequency should be less than {0}.').format(
                        settings.MAX_FREQUENCY_FOR_RANGE
                    )
                }
            )


@python_2_unicode_compatible
class StationStatusLog(models.Model):
    """Model for keeping Status log for Station."""
    station = models.ForeignKey(
        Station, related_name='station_logs', on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.IntegerField(choices=STATION_STATUSES, default=0)
    changed = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed']
        indexes = [models.Index(fields=['-changed'])]

    def __str__(self):
        return '{0} - {1}'.format(self.station, self.status)


@python_2_unicode_compatible
class Satellite(models.Model):
    """Model for SatNOGS satellites."""
    norad_cat_id = models.PositiveIntegerField(db_index=True)
    norad_follow_id = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=45)
    names = models.TextField(blank=True)
    image = models.CharField(max_length=100, blank=True, null=True)
    manual_tle = models.BooleanField(default=False)
    status = models.CharField(
        choices=list(zip(SATELLITE_STATUS, SATELLITE_STATUS)), max_length=10, default='alive'
    )

    class Meta:
        ordering = ['norad_cat_id']

    def get_image(self):
        """Return the station image or the default if doesn't exist one"""
        if self.image:
            return self.image
        return settings.SATELLITE_DEFAULT_IMAGE

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Tle(models.Model):
    """Model for TLEs."""
    tle0 = models.CharField(max_length=100, blank=True, db_index=True)
    tle1 = models.CharField(max_length=200, blank=True)
    tle2 = models.CharField(max_length=200, blank=True)
    tle_source = models.CharField(max_length=300, blank=True)
    updated = models.DateTimeField(auto_now=True, blank=True)
    satellite = models.ForeignKey(
        Satellite, related_name='tles', on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        ordering = ['tle0']

    def __str__(self):
        return '{:d} - {:s}'.format(self.id, self.tle0)

    @property
    def str_array(self):
        """Return TLE in string array format"""
        # tle fields are unicode, pyephem and others expect python strings
        return [str(self.tle0), str(self.tle1), str(self.tle2)]


class LatestTleManager(models.Manager):  # pylint: disable=R0903
    """Django Manager for latest Tle objects"""
    def get_queryset(self):
        """Returns query of latest Tle

        :returns: the latest Tle for each Satellite
        """
        subquery = Tle.objects.filter(satellite=OuterRef('satellite')).order_by('-updated')
        return super(LatestTleManager,
                     self).get_queryset().filter(updated=Subquery(subquery.values('updated')[:1]))


@python_2_unicode_compatible
class LatestTle(Tle):
    """LatestTle is the latest entry of a Satellite Tle objects
    """
    objects = LatestTleManager()

    class Meta:
        proxy = True

    def __str__(self):
        return '{:d} - {:s}'.format(self.id, self.tle0)


@python_2_unicode_compatible
class Transmitter(models.Model):
    """Model for antennas transponders."""
    uuid = ShortUUIDField(db_index=True)
    sync_to_db = models.BooleanField(default=False)

    def __str__(self):
        return self.uuid


@python_2_unicode_compatible
class Observation(models.Model):
    """Model for SatNOGS observations."""
    satellite = models.ForeignKey(
        Satellite, related_name='observations', on_delete=models.SET_NULL, null=True, blank=True
    )
    tle = models.ForeignKey(
        Tle, related_name='observations', on_delete=models.SET_NULL, null=True, blank=True
    )
    author = models.ForeignKey(
        User, related_name='observations', on_delete=models.SET_NULL, null=True, blank=True
    )
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)
    ground_station = models.ForeignKey(
        Station, related_name='observations', on_delete=models.SET_NULL, null=True, blank=True
    )
    client_version = models.CharField(max_length=255, blank=True)
    client_metadata = models.TextField(blank=True)
    payload = models.FileField(upload_to=_name_obs_files, blank=True, null=True)
    waterfall = models.ImageField(upload_to=_name_obs_files, blank=True, null=True)
    vetted_datetime = models.DateTimeField(null=True, blank=True)
    vetted_user = models.ForeignKey(
        User, related_name='observations_vetted', on_delete=models.SET_NULL, null=True, blank=True
    )
    vetted_status = models.CharField(
        choices=OBSERVATION_STATUSES, max_length=20, default='unknown'
    )
    testing = models.BooleanField(default=False)
    rise_azimuth = models.FloatField(blank=True, null=True)
    max_altitude = models.FloatField(blank=True, null=True)
    set_azimuth = models.FloatField(blank=True, null=True)
    archived = models.BooleanField(default=False)
    archive_identifier = models.CharField(max_length=255, blank=True)
    archive_url = models.URLField(blank=True, null=True)
    transmitter_uuid = ShortUUIDField(auto=False, db_index=True)
    transmitter_description = models.TextField(default='')
    transmitter_type = models.CharField(
        choices=list(zip(TRANSMITTER_TYPE, TRANSMITTER_TYPE)),
        max_length=11,
        default='Transmitter'
    )
    transmitter_uplink_low = models.BigIntegerField(blank=True, null=True)
    transmitter_uplink_high = models.BigIntegerField(blank=True, null=True)
    transmitter_uplink_drift = models.IntegerField(blank=True, null=True)
    transmitter_downlink_low = models.BigIntegerField(blank=True, null=True)
    transmitter_downlink_high = models.BigIntegerField(blank=True, null=True)
    transmitter_downlink_drift = models.IntegerField(blank=True, null=True)
    transmitter_mode = models.CharField(max_length=25, blank=True, null=True)
    transmitter_invert = models.BooleanField(default=False)
    transmitter_baud = models.FloatField(validators=[MinValueValidator(0)], blank=True, null=True)
    transmitter_created = models.DateTimeField(default=now)

    objects = ObservationManager.as_manager()

    @property
    def is_past(self):
        """Return true if observation is in the past (end time is in the past)"""
        return self.end < now()

    @property
    def is_future(self):
        """Return true if observation is in the future (end time is in the future)"""
        return self.end > now()

    @property
    def is_started(self):
        """Return true if observation has started (start time is in the past)"""
        return self.start < now()

    # this payload has been vetted good/bad/failed by someone
    @property
    def is_vetted(self):
        """Return true if observation is vetted"""
        return not self.vetted_status == 'unknown'

    # this payload has been vetted as good by someone
    @property
    def is_good(self):
        """Return true if observation is vetted as good"""
        return self.vetted_status == 'good'

    # this payload has been vetted as bad by someone
    @property
    def is_bad(self):
        """Return true if observation is vetted as bad"""
        return self.vetted_status == 'bad'

    # this payload has been vetted as failed by someone
    @property
    def is_failed(self):
        """Return true if observation is vetted as failed"""
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
        if not self.payload:
            return False
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
        """Return url for observation's audio file"""
        if self.has_audio:
            if self.archive_url:
                try:
                    request = requests.get(self.archive_url, allow_redirects=False)
                    request.raise_for_status()

                    url = request.headers['Location']
                    return url
                except requests.exceptions.RequestException as error:
                    logger = logging.getLogger(__name__)
                    logger.warning("Error in request to '%s'. Error: %s", self.archive_url, error)
                    return ''
            else:
                return self.payload.url
        return ''

    class Meta:
        ordering = ['-start', '-end']
        indexes = [models.Index(fields=['-start', '-end'])]

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        """Return absolute url of the model object"""
        return reverse('base:observation_view', kwargs={'observation_id': self.id})


@receiver(models.signals.post_delete, sender=Observation)
def observation_remove_files(sender, instance, **kwargs):  # pylint: disable=W0613
    """Remove audio and waterfall files of an observation if the observation is deleted"""
    if instance.payload:
        if os.path.isfile(instance.payload.path):
            os.remove(instance.payload.path)
    if instance.waterfall:
        if os.path.isfile(instance.waterfall.path):
            os.remove(instance.waterfall.path)


@python_2_unicode_compatible
class DemodData(models.Model):
    """Model for DemodData."""
    observation = models.ForeignKey(
        Observation, related_name='demoddata', on_delete=models.CASCADE
    )
    payload_demod = models.FileField(upload_to=_name_obs_demoddata, unique=True)
    copied_to_db = models.BooleanField(default=False)

    def is_image(self):
        """Return true if data file is an image"""
        with open(self.payload_demod.path, 'rb') as file_path:
            try:
                Image.open(file_path)
            except (IOError, TypeError):
                return False
            else:
                return True

    def display_payload_hex(self):
        """
        Return the content of the data file as hex dump of the following form: `DE AD C0 DE`.
        """
        with open(self.payload_demod.path, 'rb') as data_file:
            payload = data_file.read()

        return _decode_pretty_hex(payload)

    def display_payload_utf8(self):
        """
        Return the content of the data file decoded as UTF-8. If this fails,
        show as hex dump.
        """
        with open(self.payload_demod.path, 'rb') as data_file:
            payload = data_file.read()

        try:
            return payload.decode('utf-8')
        except UnicodeDecodeError:
            return _decode_pretty_hex(payload)

    def __str__(self):
        return '{} - {}'.format(self.id, self.payload_demod)


@receiver(models.signals.post_delete, sender=DemodData)
def demoddata_remove_files(sender, instance, **kwargs):  # pylint: disable=W0613
    """Remove data file of an observation if the observation is deleted"""
    if instance.payload_demod:
        if os.path.isfile(instance.payload_demod.path):
            os.remove(instance.payload_demod.path)
