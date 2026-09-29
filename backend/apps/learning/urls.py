"""
Learning Feature URL Routes
===========================
"""

from django.urls import path
from . import views

urlpatterns = [
    path('learn/', views.learn_course_dashboard, name='learn_dashboard'),
    path('learn/lesson/<int:lesson_id>/', views.learn_lesson_view, name='learn_lesson'),
    path('learn/lesson/<int:lesson_id>/complete/', views.learn_complete_lesson_api, name='learn_complete_lesson'),
    path('learn/section/<int:section_id>/', views.learn_section_view, name='learn_section'),
    path('learn/section/<int:section_id>/completed/', views.learn_section_completed_view, name='learn_section_completed'),
    path('learn/section/<int:section_id>/practice/', views.learn_practice_view, name='learn_practice'),
    path('learn/section/<int:section_id>/practice/search/', views.learn_practice_search_api, name='learn_practice_search'),
    path('learn/section/<int:section_id>/practice/lookup/', views.learn_practice_lookup_api, name='learn_practice_lookup'),
    path('learn/section/<int:section_id>/practice/analyze/', views.learn_practice_analyze_api, name='learn_practice_analyze'),
    path('learn/section/<int:section_id>/practice/attempts/', views.learn_practice_attempts_api, name='learn_practice_attempts'),
]
