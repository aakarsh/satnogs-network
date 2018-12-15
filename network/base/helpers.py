from rest_framework.authtoken.models import Token


def get_apikey(user):
    try:
        token = Token.objects.get(user=user)
    except Token.DoesNotExist:
        token = Token.objects.create(user=user)
    return token
