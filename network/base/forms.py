"""SatNOGS Network django base Forms class"""
from django.conf import settings
from django.forms import BaseFormSet, BaseInlineFormSet, CharField, DateTimeField, FloatField, \
    Form, ImageField, IntegerField, ModelChoiceField, ModelForm, ValidationError, \
    formset_factory, inlineformset_factory

from network.base.db_api import DBConnectionError, get_tle_sets_by_norad_id_set, \
    get_transmitters_by_uuid_set
from network.base.models import Antenna, FrequencyRange, Observation, Station
from network.base.perms import UserNoPermissionError, check_schedule_perms_per_station
from network.base.validators import ObservationOverlapError, OutOfRangeError, check_end_datetime, \
    check_overlaps, check_start_datetime, check_start_end_datetimes, \
    check_transmitter_station_pairs


class ObservationForm(ModelForm):
    """Model Form class for Observation objects"""
    start = DateTimeField(
        input_formats=['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'],
        error_messages={
            'invalid': 'Start datetime should have either "%Y-%m-%d %H:%M:%S.%f" or '
            '"%Y-%m-%d %H:%M:%S" '
            'format.',
            'required': 'Start datetime is required.'
        }
    )
    end = DateTimeField(
        input_formats=['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'],
        error_messages={
            'invalid': 'End datetime should have either "%Y-%m-%d %H:%M:%S.%f" or '
            '"%Y-%m-%d %H:%M:%S" '
            'format.',
            'required': 'End datetime is required.'
        }
    )
    ground_station = ModelChoiceField(
        queryset=Station.objects.filter(status__gt=0),
        error_messages={
            'invalid_choice': 'Station(s) should exist and be online.',
            'required': 'Station is required.'
        }
    )

    def clean_start(self):
        """Validates start datetime of a new observation"""
        start = self.cleaned_data['start']
        try:
            check_start_datetime(start)
        except ValueError as error:
            raise ValidationError(error, code='invalid') from error
        return start

    def clean_end(self):
        """Validates end datetime of a new observation"""
        end = self.cleaned_data['end']
        try:
            check_end_datetime(end)
        except ValueError as error:
            raise ValidationError(error, code='invalid') from error
        return end

    def clean(self):
        """Validates combination of start and end datetimes of a new observation"""
        if any(self.errors):
            # If there are errors in fields validation no need for validating the form
            return
        cleaned_data = super().clean()
        start = cleaned_data['start']
        end = cleaned_data['end']
        try:
            check_start_end_datetimes(start, end)
        except ValueError as error:
            raise ValidationError(error, code='invalid') from error

    class Meta:
        model = Observation
        fields = ['transmitter_uuid', 'start', 'end', 'ground_station']
        error_messages = {'transmitter_uuid': {'required': "Transmitter is required"}}


class BaseObservationFormSet(BaseFormSet):
    """Base FormSet class for Observation objects forms"""
    transmitters = {}
    tle_sets = set()

    def __init__(self, user, *args, **kwargs):
        """Initializes Observation FormSet"""
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        """Validates Observation FormSet data"""
        if any(self.errors):
            # If there are errors in forms validation no need for validating the formset
            return

        station_list = []
        transmitter_uuid_set = set()
        transmitter_uuid_station_list = []
        start_end_per_station = {}

        for form in self.forms:
            station = form.cleaned_data.get('ground_station')
            transmitter_uuid = form.cleaned_data.get('transmitter_uuid')
            start = form.cleaned_data.get('start')
            end = form.cleaned_data.get('end')
            station_id = int(station.id)
            station_list.append(station)
            transmitter_uuid_set.add(transmitter_uuid)
            transmitter_uuid_station_list.append((transmitter_uuid, station))
            if station_id in start_end_per_station:
                start_end_per_station[station_id].append((start, end))
            else:
                start_end_per_station[station_id] = []
                start_end_per_station[station_id].append((start, end))

        try:
            check_overlaps(start_end_per_station)
        except ObservationOverlapError as error:
            raise ValidationError(error, code='invalid') from error

        station_list = list(set(station_list))
        try:
            check_schedule_perms_per_station(self.user, station_list)
        except UserNoPermissionError as error:
            raise ValidationError(error, code='forbidden') from error

        try:
            transmitters = get_transmitters_by_uuid_set(transmitter_uuid_set)
            self.transmitters = transmitters
            norad_id_set = {transmitters[uuid]['norad_cat_id'] for uuid in transmitter_uuid_set}
            self.tle_sets = get_tle_sets_by_norad_id_set(norad_id_set)
        except ValueError as error:
            raise ValidationError(error, code='invalid') from error
        except DBConnectionError as error:
            raise ValidationError(error) from error

        transmitter_uuid_station_set = set(transmitter_uuid_station_list)
        transmitter_station_list = [
            (transmitters[pair[0]], pair[1]) for pair in transmitter_uuid_station_set
        ]
        try:
            check_transmitter_station_pairs(transmitter_station_list)
        except OutOfRangeError as error:
            raise ValidationError(error, code='invalid') from error


ObservationFormSet = formset_factory(
    ObservationForm, formset=BaseObservationFormSet, min_num=1, validate_min=True
)


class StationForm(ModelForm):
    """Model Form class for Station objects"""
    lat = FloatField(min_value=-90.0, max_value=90.0)
    lng = FloatField(min_value=-180.0, max_value=180.0)

    class Meta:
        model = Station
        fields = [
            'name', 'image', 'alt', 'lat', 'lng', 'qthlocator', 'horizon', 'testing',
            'description', 'target_utilization'
        ]
        image = ImageField(required=False)


AntennaInlineFormSet = inlineformset_factory(  # pylint: disable=C0103
    Station,
    Antenna,
    fields=('antenna_type', ),
    extra=0,
    can_delete=True,
    max_num=settings.MAX_ANTENNAS_PER_STATION,
    validate_max=True,
)


class BaseFrequencyRangeInlineFormSet(BaseInlineFormSet):
    """Base InlineFormSet class for FrequencyRange objects forms"""
    def clean(self):
        """Validates Observation FormSet data"""
        if any(self.errors):
            # If there are errors in forms validation no need for validating the formset
            return

        ranges = []
        for form in self.forms:
            if form.cleaned_data.get('DELETE'):
                continue
            ranges.append(
                {
                    'min': form.cleaned_data.get('min_frequency'),
                    'max': form.cleaned_data.get('max_frequency')
                }
            )

        for current_index, current_range in enumerate(ranges):
            for index, frequency_range in enumerate(ranges):
                if index == current_index:
                    continue
                if (frequency_range['min'] < current_range['min']
                        and frequency_range['max'] > current_range['max']):
                    raise ValidationError(
                        'Frequency Range {0}-{1} is subset of another'
                        ' antenna frequency range ({2}-{3})'.format(
                            current_range['min'], current_range['max'], frequency_range['min'],
                            frequency_range['max']
                        ),
                        code='invalid'
                    )
                if (frequency_range['min'] > current_range['min']
                        and frequency_range['max'] < current_range['max']):
                    raise ValidationError(
                        'Frequency Range {0}-{1} is superset of another'
                        ' antenna frequency range ({2}-{3})'.format(
                            current_range['min'], current_range['max'], frequency_range['min'],
                            frequency_range['max']
                        ),
                        code='invalid'
                    )
                if not (frequency_range['min'] > current_range['max']
                        or frequency_range['max'] < current_range['min']):
                    raise ValidationError(
                        'Frequency Range {0}-{1} conflicts with another'
                        ' antenna frequency range ({2}-{3})'.format(
                            current_range['min'], current_range['max'], frequency_range['min'],
                            frequency_range['max']
                        ),
                        code='invalid'
                    )


FrequencyRangeInlineFormSet = inlineformset_factory(  # pylint: disable=C0103
    Antenna,
    FrequencyRange,
    fields=(
        'min_frequency',
        'max_frequency',
    ),
    formset=BaseFrequencyRangeInlineFormSet,
    extra=0,
    can_delete=True,
    max_num=settings.MAX_FREQUENCY_RANGES_PER_ANTENNA,
    validate_max=True,
)


class SatelliteFilterForm(Form):
    """Form class for Satellite objects"""
    norad = IntegerField(required=False)
    start = CharField(required=False)
    end = CharField(required=False)
    ground_station = IntegerField(required=False)
    transmitter = CharField(required=False)
