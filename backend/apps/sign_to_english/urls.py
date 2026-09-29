"""
Sign to English Feature URL Routes
==================================
"""

from django.urls import path
from . import views

urlpatterns = [
    path('sign-to-english/', views.sign_to_english_view, name='sign_to_english'),
    path('api/sign-to-english/predict-auto/', views.sign_to_english_predict_auto_api, name='sign_to_english_predict_auto_api'),
    path('api/sign-to-english/predict-live/', views.sign_to_english_live_api, name='sign_to_english_live_api'),
    path('api/sign-to-english/predict-alphabet/', views.sign_to_english_predict_alphabet_api, name='sign_to_english_predict_alphabet_api'),
    path('api/sign-to-english/suggest-word/', views.sign_to_english_suggest_word_api, name='sign_to_english_suggest_word_api'),
    path('api/sign-to-english/translate-tokens/', views.sign_to_english_translate_api, name='sign_to_english_translate_api'),
    path('api/sign-to-english/process-video/', views.sign_to_english_video_api, name='sign_to_english_video_api'),
    path('api/sign-to-english/status/', views.sign_to_english_status_api, name='sign_to_english_status_api'),
]
