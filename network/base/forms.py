"""SatNOGS Network django base Forms class"""
from __future__ import absolute_import

from django import forms

from network.base.db_api import DBConnectionError, get_transmitters_by_uuid_set
from network.base.models import Observation, Station
from network.base.perms import UserNoPermissionError, \
    check_schedule_perms_per_station
from network.base.validators import ObservationOverlapError, OutOfRangeError, \
    check_end_datetime, check_overlaps, check_start_datetime, \
    check_start_end_datetimes, check_transmitter_station_pairs


class ObservationForm(forms.ModelForm):
    """Model Form class for Observation objects"""
    start = forms.DateTimeField(
        input_formats=['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'],
        error_messages={
            'invalid':
            'Start datetime should have either "%Y-%m-%d %H:%M:%S.%f" or "%Y-%m-%d %H:%M:%S" '
            'format.',
            'required':
            'Start datetime is required.'
        }
    )
    end = forms.DateTimeField(
        input_formats=['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'],
        error_messages={
            'invalid':
            'End datetime should have either "%Y-%m-%d %H:%M:%S.%f" or "%Y-%m-%d %H:%M:%S" '
            'format.',
            'required':
            'End datetime is required.'
        }
    )
    ground_station = forms.ModelChoiceField(
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
            raise forms.ValidationError(error, code='invalid')
        return start

    def clean_end(self):
        """Validates end datetime of a new observation"""
        end = self.cleaned_data['end']
        try:
            check_end_datetime(end)
        except ValueError as error:
            raise forms.ValidationError(error, code='invalid')
        return end

    def clean(self):
        """Validates combination of start and end datetimes of a new observation"""
        if any(self.errors):
            # If there are errors in fields validation no need for validating the form
            return
        cleaned_data = super(ObservationForm, self).clean()
        start = cleaned_data['start']
        end = cleaned_data['end']
        try:
            check_start_end_datetimes(start, end)
        except ValueError as error:
            raise forms.ValidationError(error, code='invalid')

    class Meta:
        model = Observation
        fields = ['transmitter_uuid', 'start', 'end', 'ground_station']
        error_messages = {'transmitter_uuid': {'required': "Transmitter is required"}}


class BaseObservationFormSet(forms.BaseFormSet):
    """Base FormSet class for Observation objects forms"""
    transmitters = {}

    def __init__(self, user, *args, **kwargs):
        """Initializes Observation FormSet"""
        self.user = user
        super(BaseObservationFormSet, self).__init__(*args, **kwargs)

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
            raise forms.ValidationError(error, code='invalid')

        station_list = list(set(station_list))
        try:
            check_schedule_perms_per_station(self.user, station_list)
        except UserNoPermissionError as error:
            raise forms.ValidationError(error, code='forbidden')

        try:
            transmitters = get_transmitters_by_uuid_set(transmitter_uuid_set)
            self.transmitters = transmitters
        except ValueError as error:
            raise forms.ValidationError(error, code='invalid')
        except DBConnectionError as error:
            raise forms.ValidationError(error)

        transmitter_uuid_station_set = set(transmitter_uuid_station_list)
        transmitter_station_list = [
            (transmitters[pair[0]], pair[1]) for pair in transmitter_uuid_station_set
        ]
        try:
            check_transmitter_station_pairs(transmitter_station_list)
        except OutOfRangeError as error:
            raise forms.ValidationError(error, code='invalid')


class StationForm(forms.ModelForm):
    """Model Form class for Station objects"""
    class Meta:
        model = Station
        fields = [
            'name', 'image', 'alt', 'lat', 'lng', 'qthlocator', 'horizon', 'antenna', 'testing',
            'description', 'target_utilization'
        ]
        image = forms.ImageField(required=False)


class SatelliteFilterForm(forms.Form):
    """Form class for Satellite objects"""
    norad = forms.IntegerField(required=False)
    start = forms.CharField(required=False)
    end = forms.CharField(required=False)
    ground_station = forms.IntegerField(required=False)
    transmitter = forms.CharField(required=False)
