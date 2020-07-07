"""Django users forms for SatNOGS Network"""
from django import forms

from network.users.models import User


class UserForm(forms.ModelForm):
    """Model Form class for User objects"""
    class Meta:
        model = User
        fields = ("first_name", "last_name")
