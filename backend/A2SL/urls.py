"""A2SL URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
import os
from . import views

assets_root = getattr(settings, 'ASSETS_DIR', os.path.join(settings.BASE_DIR, 'assets'))

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': assets_root}),
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': assets_root}),

    # Feature Modules
    path('', include('apps.accounts.urls')),
    path('', include('apps.dashboard.urls')),
    path('', include('apps.upload.urls')),
    path('', include('apps.live_converter.urls')),
    path('', include('apps.learning.urls')),
    path('', include('apps.quiz.urls')),
    path('', include('apps.sign_to_english.urls')),
    path('', include('apps.concept_assessment.urls')),

    # Core App Backward-Compatibility Routes
    path('', include('study_companion.urls')),
]
