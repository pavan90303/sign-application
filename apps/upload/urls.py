"""
Upload Feature URL Routes
=========================
"""

from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_ppt_view, name='upload'),
    path('summary/<int:session_id>/', views.summary_view, name='summary'),
]
