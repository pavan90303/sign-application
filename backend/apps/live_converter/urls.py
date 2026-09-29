"""
Live Converter Feature URL Routes
=================================
"""

from django.urls import path
from . import views

urlpatterns = [
    path('live-converter/', views.animation_view, name='animation'),
    path('animation/', views.animation_view, name='animation_legacy'),
]
