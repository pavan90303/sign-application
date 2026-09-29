"""
Django settings for A2SL project.
Organized into backend and frontend structure.
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
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*']

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

ASSETS_DIR = os.path.join(PROJECT_DIR, 'frontend', 'assets') if os.path.isdir(os.path.join(PROJECT_DIR, 'frontend', 'assets')) else os.path.join(BASE_DIR, 'assets')

_staticfiles_candidates = [
    ASSETS_DIR,
    os.path.join(PROJECT_DIR, 'frontend', 'static'),
    os.path.join(BASE_DIR, 'assets'),
    os.path.join(BASE_DIR, 'static'),
]
STATICFILES_DIRS = [d for d in _staticfiles_candidates if os.path.isdir(d)]

# Media files (PPT & student video uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

# Upload size limits (50 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Google Gemini API Key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'PLACEHOLDER_KEY')

# Login URL
LOGIN_URL = 'login'
