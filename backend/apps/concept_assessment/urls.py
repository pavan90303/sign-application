"""
Concept Assessment Feature URL Routes
=====================================
"""

from django.urls import path
from . import views

urlpatterns = [
    path('concept-assessment/', views.concept_assessment_view, name='concept_assessment'),
    path('concept-assessment/save-reference/', views.concept_assessment_save_reference_api, name='concept_assessment_save_reference'),
    path('concept-assessment/analyze/', views.concept_assessment_analyze_api, name='concept_assessment_analyze'),
    path('concept-assessment/relearn/<str:concept_name>/', views.concept_assessment_relearn_api, name='concept_assessment_relearn'),
    path('concept-assessment/attempts-history/', views.concept_assessment_history_api, name='concept_assessment_history'),
    path('concept-assessment/<int:assessment_id>/teacher-review/', views.teacher_review_view, name='teacher_review'),
]
