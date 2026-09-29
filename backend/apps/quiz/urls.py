"""
Quiz Feature URL Routes
=======================
"""

from django.urls import path
from . import views

urlpatterns = [
    # Document Quiz
    path('quiz/<int:session_id>/', views.quiz_view, name='quiz'),
    path('quiz/<int:session_id>/api/', views.quiz_data_api, name='quiz_data_api'),
    path('quiz/<int:session_id>/results/', views.quiz_submit_view, name='quiz_results'),
    path('quiz/<int:session_id>/save-result/', views.quiz_save_result, name='quiz_save_result'),

    # Sign Quest & Gamified Games
    path('sign-quest/', views.sign_quest_view, name='sign_quest_game'),
    path('learn/section/<int:section_id>/quest/', views.sign_quest_view, name='sign_quest_section'),
    path('examination/', views.sign_quest_view, name='examination_game'),
    path('learn/quiz/', views.sign_quest_entry_view, name='sign_quest_quiz'),
    path('dino-game/', views.sign_quest_view, name='dino_runner_game'),
    path('dino-quiz/', views.sign_quest_entry_view, name='dino_quiz_game'),

    # Course Section Quizzes
    path('learn/section/<int:section_id>/quiz/', views.learn_quiz_view, name='learn_quiz'),
    path('learn/section/<int:section_id>/dino-quiz/', views.learn_quiz_view, name='dino_quiz_section'),
    path('learn/section/<int:section_id>/quiz/api/', views.learn_quiz_api, name='learn_quiz_api'),
    path('learn/section/<int:section_id>/quiz/check-answer/', views.learn_quiz_check_answer_api, name='learn_quiz_check_answer'),
    path('learn/section/<int:section_id>/quiz/submit/', views.learn_quiz_submit_api, name='learn_quiz_submit'),
    path('learn/section/<int:section_id>/results/', views.learn_quiz_results_view, name='learn_quiz_results'),
]
