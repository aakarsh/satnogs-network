"""SatNOGS Network Auth0 login module auth backend"""
import requests
from social_core.backends.oauth import BaseOAuth2


class Auth0(BaseOAuth2):
    """Auth0 OAuth authentication backend"""
    name = 'auth0'
    SCOPE_SEPARATOR = ' '
    ACCESS_TOKEN_METHOD = 'POST'
    EXTRA_DATA = [('email', 'email')]

    def authorization_url(self):
        """Return the authorization endpoint."""
        return "https://" + self.setting('DOMAIN') + "/authorize"

    def access_token_url(self):
        """Return the token endpoint."""
        return "https://" + self.setting('DOMAIN') + "/oauth/token"

    def auth_html(self):
        """Return the login endpoint."""
        return "https://" + self.setting('DOMAIN') + "/login/auth0"

    def get_user_id(self, details, response):
        """Return current user id."""
        return details['user_id']

    def get_user_details(self, response):
        url = 'https://' + self.setting('DOMAIN') + '/userinfo'
        headers = {'authorization': 'Bearer ' + response['access_token']}
        resp = requests.get(url, headers=headers)
        userinfo = resp.json()

        return {
            'username': userinfo['nickname'],
            'email': userinfo['email'],
            # 'first_name': userinfo['name'],
            'user_id': userinfo['sub']
        }
