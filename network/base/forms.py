from django import forms

from network.base.models import Station


class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['name', 'image', 'alt', 'lat', 'lng', 'qthlocator',
                  'horizon', 'antenna', 'testing', 'description',
                  'target_utilization']
        image = forms.ImageField(required=False)


class SatelliteFilterForm(forms.Form):
    norad = forms.IntegerField(required=False)
    start = forms.CharField(required=False)
    end = forms.CharField(required=False)
    ground_station = forms.IntegerField(required=False)
    transmitter = forms.CharField(required=False)
