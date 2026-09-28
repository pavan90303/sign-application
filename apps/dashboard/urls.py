"""
Dashboard Feature URL Routes
============================
"""

from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('history/', views.history_view, name='history'),
]
