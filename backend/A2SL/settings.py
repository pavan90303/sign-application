"""
Django settings for A2SL project.
Organized for production and Vercel serverless deployment.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# BASE_DIR is the backend directory (where apps, models, shared services live)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# PROJECT_DIR is the top-level repository root (contains frontend/ and backend/)
PROJECT_DIR = os.path.dirname(BASE_DIR)

# Load environment variables from root or backend
load_dotenv(os.path.join(PROJECT_DIR, '.env'))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# NLTK data directory
import nltk
NLTK_DATA_DIR = os.path.join(BASE_DIR, 'nltk_data')
nltk.data.path.append(NLTK_DATA_DIR)
for pkg in ['averaged_perceptron_tagger', 'wordnet', 'omw-1.4']:
    try:
        nltk.data.find(f'corpora/{pkg}' if pkg in ['wordnet', 'omw-1.4'] else f'taggers/{pkg}')
    except (LookupError, Exception):
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-3k7=!d39#4@_&5a6to&4=_=j(c^v0(vv91cj5+9e8+d4&+01jb')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# Allowed hosts configuration
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = [
        '*',
        '.vercel.app',
        'localhost',
        '127.0.0.1',
    ]

# CSRF trusted origins for Vercel HTTPS domains
csrf_trusted_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_trusted_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.vercel.app',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'study_companion',
    'apps.accounts',
    'apps.dashboard',
    'apps.upload',
    'apps.live_converter',
    'apps.learning',
    'apps.quiz',
    'apps.sign_to_english',
    'apps.concept_assessment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'A2SL.urls'

_template_dirs = [
    os.path.join(PROJECT_DIR, 'frontend', 'templates'),
    os.path.join(BASE_DIR, 'shared', 'templates'),
    os.path.join(BASE_DIR, 'templates'),
    os.path.join(PROJECT_DIR, 'templates'),
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [d for d in _template_dirs if os.path.isdir(d)],
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

WSGI_APPLICATION = 'A2SL.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'db.sqlite3'),
    }
}

# Production database support (e.g. Neon, Supabase, Railway Postgres)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    except Exception as e:
        print(f"Warning: Failed to parse DATABASE_URL: {e}")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images, Sign animation clips)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_DIR, 'staticfiles')

ASSETS_DIR = os.path.join(PROJECT_DIR, 'frontend', 'assets') if os.path.isdir(os.path.join(PROJECT_DIR, 'frontend', 'assets')) else os.path.join(BASE_DIR, 'assets')

_staticfiles_candidates = [
    ASSETS_DIR,
    os.path.join(PROJECT_DIR, 'frontend', 'static'),
    os.path.join(BASE_DIR, 'assets'),
    os.path.join(BASE_DIR, 'static'),
]
STATICFILES_DIRS = [d for d in _staticfiles_candidates if os.path.isdir(d)]

# WhiteNoise compressed static files storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Media files (PPT & student video uploads)
MEDIA_URL = '/media/'
if os.environ.get('VERCEL'):
    MEDIA_ROOT = '/tmp/media'
else:
    MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

# Upload size limits (50 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'PLACEHOLDER_KEY')

# Login URL
LOGIN_URL = 'login'
