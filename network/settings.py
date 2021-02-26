"""SatNOGS Network Application django settings

For local installation settings please copy .env-dist to .env and edit
the appropriate settings in that file. You should not need to edit this
file for local settings!
"""
from decouple import Csv, config
from dj_database_url import parse as db_url
from sentry_sdk import init as sentry_sdk_init
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from unipath import Path

from network import __version__

ROOT = Path(__file__).parent

ENVIRONMENT = config('ENVIRONMENT', default='dev')
DEBUG = config('DEBUG', default=True, cast=bool)
AUTH0 = config('AUTH0', default=False, cast=bool)

# Apps
DJANGO_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
)
THIRD_PARTY_APPS = (
    'avatar',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'django_filters',
    'crispy_forms',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'compressor',
    'csp',
)
LOCAL_APPS = (
    'network.users',
    'network.base',
    'network.api',
)

if DEBUG:
    DJANGO_APPS += ('debug_toolbar', )
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: request.environ.get('SERVER_NAME', None) !=
        'testserver',
    }
if AUTH0:
    THIRD_PARTY_APPS += ('social_django', )
    LOCAL_APPS += ('auth0login', )

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middlware
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
)

if DEBUG:
    MIDDLEWARE = ('debug_toolbar.middleware.DebugToolbarMiddleware', ) + MIDDLEWARE

# Email
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=300, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@satnogs.org')
EMAIL_FOR_STATIONS_ISSUES = config('EMAIL_FOR_STATIONS_ISSUES', default='')
ADMINS = [('SatNOGS Admins', DEFAULT_FROM_EMAIL)]
MANAGERS = ADMINS
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Cache
CACHES = {
    'default': {
        'BACKEND': config(
            'CACHE_BACKEND',
            default='django.core.cache.backends.locmem.LocMemCache',
        ),
        'LOCATION': config('CACHE_LOCATION', default='unique-location'),
        'OPTIONS': {
            'MAX_ENTRIES': 5000,
            'CLIENT_CLASS': config('CACHE_CLIENT_CLASS', default=''),
        },
        'KEY_PREFIX': 'network-{0}'.format(ENVIRONMENT),
    }
}
CACHE_TTL = config('CACHE_TTL', default=300, cast=int)

# Internationalization
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False
USE_L10N = False
USE_TZ = True

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            Path(ROOT).child('templates').resolve(),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'network.base.context_processors.analytics',
                'network.base.context_processors.stage_notice',
                'network.base.context_processors.user_processor',
                'network.base.context_processors.auth_block',
                'network.base.context_processors.logout_block',
                'network.base.context_processors.version'
            ],
            'loaders': [
                (
                    'django.template.loaders.cached.Loader', [
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    ]
                ),
            ],
        },
    },
]

# Static & Media
STATIC_ROOT = config('STATIC_ROOT', default=Path('staticfiles').resolve())
STATIC_URL = config('STATIC_URL', default='/static/')
STATICFILES_DIRS = [
    Path(ROOT).child('static').resolve(),
]
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
MEDIA_ROOT = config('MEDIA_ROOT', default=Path('media').resolve())
FILE_UPLOAD_TEMP_DIR = config('FILE_UPLOAD_TEMP_DIR', default=Path('/tmp').resolve())
MEDIA_URL = config('MEDIA_URL', default='/media/')
CRISPY_TEMPLATE_PACK = 'bootstrap3'
STATION_DEFAULT_IMAGE = '/static/img/ground_station_no_image.png'
SATELLITE_DEFAULT_IMAGE = 'https://db.satnogs.org/static/img/sat.png'
COMPRESS_ENABLED = config('COMPRESS_ENABLED', default=False, cast=bool)
COMPRESS_OFFLINE = config('COMPRESS_OFFLINE', default=False, cast=bool)
COMPRESS_CACHE_BACKEND = config('COMPRESS_CACHE_BACKEND', default='default')
COMPRESS_FILTERS = {
    'css': [
        'compressor.filters.css_default.CssAbsoluteFilter',
        'compressor.filters.cssmin.rCSSMinFilter'
    ]
}
COMPRESS_PRECOMPILERS = (('text/scss', 'sass --scss {infile} {outfile}'), )

# App conf
ROOT_URLCONF = 'network.urls'
WSGI_APPLICATION = 'network.wsgi.application'
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Auth
AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend', )
if AUTH0:
    AUTHENTICATION_BACKENDS += ('auth0login.auth0backend.Auth0', )

ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
AUTH_USER_MODEL = 'users.User'
LOGIN_REDIRECT_URL = 'users:redirect_user'
if AUTH0:
    LOGIN_URL = '/login/auth0'
    LOGOUT_REDIRECT_URL = 'https://' + config('SOCIAL_AUTH_AUTH0_DOMAIN') + \
                          '/v2/logout?returnTo=' + config('SITE_URL')
else:
    LOGIN_URL = 'account_login'
    LOGOUT_REDIRECT_URL = '/'
AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s - %(process)d %(thread)d - %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'django.network.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'network': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
    }
}

# Sentry
SENTRY_ENABLED = config('SENTRY_ENABLED', default=False, cast=bool)
if SENTRY_ENABLED:
    sentry_sdk_init(
        environment=ENVIRONMENT,
        dsn=config('SENTRY_DSN', default=''),
        release='satnogs-network@{}'.format(__version__),
        integrations=[CeleryIntegration(),
                      DjangoIntegration(),
                      RedisIntegration()]
    )

# Celery
CELERY_ENABLE_UTC = USE_TZ
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_RESULTS_EXPIRES = 3600
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_SEND_TASK_ERROR_EMAILS = True
CELERY_TASK_ALWAYS_EAGER = False
CELERY_DEFAULT_QUEUE = 'network-{0}-queue'.format(ENVIRONMENT)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
REDIS_CONNECT_RETRY = True
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': config('REDIS_VISIBILITY_TIMEOUT', default=604800, cast=int),
    'fanout_prefix': True
}

# API
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework.authentication.TokenAuthentication', ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend', ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
SPECTACULAR_DEFAULTS = {
    'SCHEMA_PATH_PREFIX': r'/api',
    'DEFAULT_GENERATOR_CLASS': 'drf_spectacular.generators.SchemaGenerator',
    'COMPONENT_SPLIT_REQUEST': True,
    'TITLE': 'SatNOGS Network',
    'DESCRIPTION': 'SatNOGS Network is a web application, implementing a global scheduling and'
    'monitoring network for ground station operations.',
    'CONTACT': {
        'name': 'SatNOGS Developer Chat',
        'url': 'https://riot.im/app/#/room/#satnogs-dev:matrix.org'
    },
    'LICENSE': {
        'name': 'AGPL 3.0',
        'url': 'https://www.gnu.org/licenses/agpl-3.0.html'
    },
    'VERSION': '1.1',
    'SERVERS': [
        {
            'url': 'https://network-dev.satnogs.org',
            'description': 'Development server'
        }, {
            'url': 'https://network.satnogs.org',
            'description': 'Production server'
        }
    ],
    'EXTERNAL_DOCS': {
        'url': 'https://wiki.satnogs.org',
        'description': 'SatNOGS Wiki'
    },
}

# Security
SECRET_KEY = config('SECRET_KEY', default='changeme')
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
CSP_DEFAULT_SRC = config(
    'CSP_DEFAULT_SRC',
    cast=lambda v: tuple(s.strip() for s in v.split(',')),
    default="'self',"
    'https://*.mapbox.com,'
    'https://archive.org,'
    'https://*.archive.org'
)
CSP_SCRIPT_SRC = config(
    'CSP_SCRIPT_SRC',
    cast=lambda v: tuple(s.strip() for s in v.split(',')),
    default="'self',"
    'https://*.google-analytics.com,'
    "'unsafe-eval'"
)
CSP_IMG_SRC = config(
    'CSP_IMG_SRC',
    cast=lambda v: tuple(s.strip() for s in v.split(',')),
    default="'self',"
    'https://*.gravatar.com,'
    'https://*.mapbox.com,'
    'https://*.satnogs.org,'
    'https://*.google-analytics.com,'
    'data:,'
    'blob:'
)
CSP_STYLE_SRC = config(
    'CSP_STYLE_SRC',
    cast=lambda v: tuple(s.strip() for s in v.split(',')),
    default="'self',"
    "'unsafe-inline'"
)
CSP_WORKER_SRC = config(
    'CSP_WORKER_SRC', cast=lambda v: tuple(s.strip() for s in v.split(',')), default='blob:'
)
CSP_FRAME_SRC = config(
    'CSP_FRAME_SRC', cast=lambda v: tuple(s.strip() for s in v.split(',')), default='blob:'
)
CSP_CHILD_SRC = config(
    'CSP_CHILD_SRC', cast=lambda v: tuple(s.strip() for s in v.split(',')), default='blob:'
)

# Database
DATABASE_URL = config('DATABASE_URL', default='sqlite:///db.sqlite3')
DATABASES = {'default': db_url(DATABASE_URL)}
DATABASES_EXTRAS = {
    'OPTIONS': {
        'init_command': 'SET sql_mode="STRICT_TRANS_TABLES"'
    },
}
if DATABASES['default']['ENGINE'].split('.')[-1] == 'mysql':
    DATABASES['default'].update(DATABASES_EXTRAS)

# Mapbox API
MAPBOX_GEOCODE_URL = 'https://api.tiles.mapbox.com/v4/geocode/mapbox.places/'
MAPBOX_MAP_ID = config('MAPBOX_MAP_ID', default='pierros.jbf6la1j')
MAPBOX_TOKEN = config('MAPBOX_TOKEN', default='')

# TLE Sources
TLE_SOURCES_JSON = config('TLE_SOURCES_JSON', default='')

# SpaceTrack.org Credentials
SPACE_TRACK_USERNAME = config('SPACE_TRACK_USERNAME', default='')
SPACE_TRACK_PASSWORD = config('SPACE_TRACK_PASSWORD', default='')

# Observations settings
# Datetimes in minutes for scheduling OPTIONS
OBSERVATION_DATE_MIN_START = config('OBSERVATION_DATE_MIN_START', default=10, cast=int)
OBSERVATION_DATE_MIN_END = config('OBSERVATION_DATE_MIN_END', default=20, cast=int)
# Deletion range in minutes
OBSERVATION_DATE_MAX_RANGE = config('OBSERVATION_DATE_MAX_RANGE', default=2890, cast=int)
# Clean up threshold in days
OBSERVATION_OLD_RANGE = config('OBSERVATION_OLD_RANGE', default=30, cast=int)
# Minimum duration of observation in seconds
OBSERVATION_DURATION_MIN = config('OBSERVATION_DURATION_MIN', default=120, cast=int)
# Minimum observations for showing warning on scheduling
OBSERVATION_WARN_MIN_OBS = config('OBSERVATION_WARN_MIN_OBS', default=30, cast=int)
# Cache expiration of the lock for "archive audio" task
ARCHIVE_AUDIO_LOCK_EXPIRATION = config('ARCHIVE_AUDIO_LOCK_EXPIRATION', default=900, cast=int)
# Modes, in comma separated list, of which demoded data should not be send to DB
NOT_SYNCED_MODES = config(
    'NOT_SYNCED_MODES', default='AHRPT,AM,APT,CW,FM,FMN,HRPT,LRPT,LSB,SSTV,USB', cast=Csv()
)

# Station settings
# Heartbeat for keeping a station online in minutes
STATION_HEARTBEAT_TIME = config('STATION_HEARTBEAT_TIME', default=60, cast=int)
# Maximum window for upcoming passes in hours
STATION_UPCOMING_END = config('STATION_UPCOMING_END', default=24, cast=int)
WIKI_STATION_URL = config('WIKI_STATION_URL', default='https://wiki.satnogs.org/')
MAX_ANTENNAS_PER_STATION = config('MAX_ANTENNAS_PER_STATION', default=4, cast=int)
MAX_FREQUENCY_RANGES_PER_ANTENNA = config('MAX_FREQUENCY_RANGES_PER_ANTENNA', default=5, cast=int)
MAX_FREQUENCY_FOR_RANGE = config('MAX_FREQUENCY_FOR_RANGE', default=40000000000, cast=int)
MIN_FREQUENCY_FOR_RANGE = config('MIN_FREQUENCY_FOR_RANGE', default=300, cast=int)
VHF_MIN_FREQUENCY = config('VHF_MIN_FREQUENCY', default=135000000, cast=int)
VHF_MAX_FREQUENCY = config('VHF_MAX_FREQUENCY', default=148000000, cast=int)
UHF_MIN_FREQUENCY = config('UHF_MIN_FREQUENCY', default=430000000, cast=int)
UHF_MAX_FREQUENCY = config('UHF_MAX_FREQUENCY', default=470000000, cast=int)
L_MIN_FREQUENCY = config('L_MIN_FREQUENCY', default=1050000000, cast=int)
L_MAX_FREQUENCY = config('L_MAX_FREQUENCY', default=1750000000, cast=int)
S_MIN_FREQUENCY = config('S_MIN_FREQUENCY', default=2200000000, cast=int)
S_MAX_FREQUENCY = config('S_MAX_FREQUENCY', default=2450000000, cast=int)

# Station status check
# How often, in seconds, will the check for observations with no results runs
OBS_NO_RESULTS_CHECK_PERIOD = config('OBS_NO_RESULTS_CHECK_PERIOD', default=21600, cast=int)
# Minimum of observations to check for not returning results for each station
OBS_NO_RESULTS_MIN_COUNT = config('OBS_NO_RESULTS_MIN_COUNT', default=3, cast=int)
# How long, in seconds, from the end of an observation without results, check ignores it.
OBS_NO_RESULTS_IGNORE_TIME = config('OBS_NO_RESULTS_IGNORE_TIME', default=1800, cast=int)

# DB API
# Set DB_API_ENDOINT to '' to disable the data fetching from DB
DB_API_ENDPOINT = config('DB_API_ENDPOINT', default='https://db.satnogs.org/api/')

# API timeout in seconds
DB_API_TIMEOUT = config('DB_API_TIMEOUT', default=2.0, cast=float)

# API key for DB
DB_API_KEY = config('DB_API_KEY', default='')

# Timeout in seconds for the community forum
# (used e.g. when checking for the existance of certain threads)
COMMUNITY_TIMEOUT = config('COMMUNITY_TIMEOUT', default=2.0, cast=float)

# ListView pagination
ITEMS_PER_PAGE = config('ITEMS_PER_PAGE', default=25, cast=int)

# User settings
AVATAR_GRAVATAR_DEFAULT = config('AVATAR_GRAVATAR_DEFAULT', default='mm')

# Cache expiration of the lock for "process audio" task
PROCESS_AUDIO_LOCK_EXPIRATION = config('PROCESS_AUDIO_LOCK_EXPIRATION', default=900, cast=int)

# Audio zip
ZIP_AUDIO_FILES = config('ZIP_AUDIO_FILES', default=False, cast=bool)
AUDIO_FILES_PER_ZIP = config('AUDIO_FILES_PER_ZIP', default=1000, cast=int)
ZIP_FILE_PREFIX = config('ZIP_FILE_PREFIX', default='satnogs-observations')
# Audio zip - Expiration time for access lock when append audio file to zip
ZIP_AUDIO_LOCK_EXPIRATION = config('ZIP_AUDIO_LOCK_EXPIRATION', default=600, cast=int)
# Audio zip - Cache expiration of the lock for "zip audio" task
ZIP_TASK_LOCK_EXPIRATION = config('ZIP_TASK_LOCK_EXPIRATION', default=3600, cast=int)

# Archive.org
ARCHIVE_ZIP_FILES = config('ARCHIVE_ZIP_FILES', default=False, cast=bool)
ZIP_FILES_PER_ITEM = config('ZIP_FILES_PER_ITEM', default=10, cast=int)
ITEM_IDENTIFIER_PREFIX = config('ITEM_IDENTIFIER_PREFIX', default='satnogs-observations')
ITEM_TITLE_PREFIX = config('ITEM_TITLE_PREFIX', default='SatNOGS Observations')
# Archive.org - Cache expiration of the lock for "archive audio" task
ARCHIVE_TASK_LOCK_EXPIRATION = config('ARCHIVE_TASK_LOCK_EXPIRATION', default=86400, cast=int)
# Archive.org - Expiration time for access lock when archiving zip file
ARCHIVE_ZIP_LOCK_EXPIRATION = config('ARCHIVE_ZIP_LOCK_EXPIRATION', default=21600, cast=int)
# Archive.org - Hours from end time of the timely last observation of a group
ARCHIVE_SKIP_TIME = config('ARCHIVE_SKIP_TIME', default=48, cast=int)
S3_ACCESS_KEY = config('S3_ACCESS_KEY', default='')
S3_SECRET_KEY = config('S3_SECRET_KEY', default='')
S3_RETRIES_ON_SLOW_DOWN = config('S3_RETRIES_ON_SLOW_DOWN', default=1, cast=int)
S3_RETRIES_SLEEP = config('S3_RETRIES_SLEEP', default=30, cast=int)
ARCHIVE_COLLECTION = config('ARCHIVE_COLLECTION', default='test_collection')
ARCHIVE_MEDIA_TYPE = config('ARCHIVE_MEDIA_TYPE', default='data')
ARCHIVE_URL = 'https://archive.org/download/'
REMOVE_ARCHIVED_AUDIO_FILES = config('REMOVE_ARCHIVED_AUDIO_FILES', default=False, cast=bool)
REMOVE_ARCHIVED_ZIP_FILE = config('REMOVE_ARCHIVED_ZIP_FILE', default=False, cast=bool)

if AUTH0:
    SOCIAL_AUTH_TRAILING_SLASH = False  # Remove end slash from routes
    SOCIAL_AUTH_AUTH0_DOMAIN = config('SOCIAL_AUTH_AUTH0_DOMAIN', default='YOUR_AUTH0_DOMAIN')
    SOCIAL_AUTH_AUTH0_KEY = config('SOCIAL_AUTH_AUTH0_KEY', default='YOUR_CLIENT_ID')
    SOCIAL_AUTH_AUTH0_SECRET = config('SOCIAL_AUTH_AUTH0_SECRET', default='YOUR_CLIENT_SECRET')
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
    SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email', 'first_name', 'last_name']

    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.auth_allowed',
        'social_core.pipeline.social_auth.social_user',
        'social_core.pipeline.social_auth.associate_by_email',
        'social_core.pipeline.user.get_username',
        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details',
    )

    SOCIAL_AUTH_AUTH0_SCOPE = [
        'openid',
        'email',
        'profile',
    ]

if ENVIRONMENT == 'dev':
    # Disable template caching
    for backend in TEMPLATES:
        del backend['OPTIONS']['loaders']
        backend['APP_DIRS'] = True

# needed to ensure data_obs files can be read by nginx
FILE_UPLOAD_PERMISSIONS = 0o0644
