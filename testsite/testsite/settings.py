# Be careful about any settings you COPY from this file
# Multiple settings are here to make things easier to test
# They will make your site less secure.
import os

from pathlib import Path
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


# Configure FIDO_SERVER_ID this with something real for testing
# cloudflared is a quick and easy service to expose this to the
# real world but it's only a temporary name, so you'll need to
# update this.
MULTIFACTOR = {
    'FIDO_SERVER_ID': os.environ.get('DOMAIN', 'localhost'),
    'FALLBACKS': {
        'debug-console': (lambda user: user,
                    'multifactor.factors.fallback.debug_print_console'),
        'email': (lambda user: user.email, 'multifactor.factors.fallback.send_email'),
    }
}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SECRET_KEY = 'zng@fpiuz-n#6&cys3h&6+s-pegop#iqm!$_-86cu_pb_(*ugy'

DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "django_extensions",
    "debug_toolbar",

    "multifactor",
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'testsite.disable_csrf.DisableCSRFMiddleware',  # disables CSRF globally
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'testsite.urls'
LOGIN_URL = 'admin:login'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'

INTERNAL_IPS = [
    "127.0.0.1",
]