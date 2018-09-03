from django import forms

from network.base.models import Station


class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['name', 'image', 'alt', 'rig', 'lat', 'lng', 'qthlocator',
                  'horizon', 'antenna', 'testing', 'description']
        image = forms.ImageField(required=False)


class SatelliteFilterForm(forms.Form):
    norad = forms.IntegerField(required=False)
    start_date = forms.CharField(required=False)
    end_date = forms.CharField(required=False)
    ground_station = forms.IntegerField(required=False)
    transmitter = forms.CharField(required=False)
