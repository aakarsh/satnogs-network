"""SatNOGS Network Auth0 login module views"""
from django.shortcuts import render


def index(request):
    """Returns the index view"""
    return render(request, 'index.html')
