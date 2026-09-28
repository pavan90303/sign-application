from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_ppt_view, name='upload'),
    path('summary/<int:session_id>/', views.summary_view, name='summary'),
    path('quiz/<int:session_id>/', views.quiz_view, name='quiz'),
    path('quiz/<int:session_id>/api/', views.quiz_data_api, name='quiz_data_api'),
    path('quiz/<int:session_id>/results/', views.quiz_submit_view, name='quiz_results'),
    path('quiz/<int:session_id>/save-result/', views.quiz_save_result, name='quiz_save_result'),
    path('live-converter/', views.animation_view, name='animation'),
    path('history/', views.history_view, name='history'),

    # Learn Sign Language Feature
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
    path('sign-quest/', views.sign_quest_view, name='sign_quest_game'),
    path('learn/section/<int:section_id>/quest/', views.sign_quest_view, name='sign_quest_section'),
    path('examination/', views.sign_quest_view, name='examination_game'),
    path('learn/quiz/', views.sign_quest_entry_view, name='sign_quest_quiz'),
    path('dino-game/', views.sign_quest_view, name='dino_runner_game'),
    path('dino-quiz/', views.sign_quest_entry_view, name='dino_quiz_game'),
    path('learn/section/<int:section_id>/quiz/', views.learn_quiz_view, name='learn_quiz'),
    path('learn/section/<int:section_id>/dino-quiz/', views.learn_quiz_view, name='dino_quiz_section'),
    path('learn/section/<int:section_id>/quiz/api/', views.learn_quiz_api, name='learn_quiz_api'),
    path('learn/section/<int:section_id>/quiz/check-answer/', views.learn_quiz_check_answer_api, name='learn_quiz_check_answer'),
    path('learn/section/<int:section_id>/quiz/submit/', views.learn_quiz_submit_api, name='learn_quiz_submit'),
    path('learn/section/<int:section_id>/results/', views.learn_quiz_results_view, name='learn_quiz_results'),

    # Concept Understanding Assessment Feature
    path('concept-assessment/', views.concept_assessment_view, name='concept_assessment'),
    path('concept-assessment/save-reference/', views.concept_assessment_save_reference_api, name='concept_assessment_save_reference'),
    path('concept-assessment/analyze/', views.concept_assessment_analyze_api, name='concept_assessment_analyze'),
    path('concept-assessment/relearn/<str:concept_name>/', views.concept_assessment_relearn_api, name='concept_assessment_relearn'),
    path('concept-assessment/attempts-history/', views.concept_assessment_history_api, name='concept_assessment_history'),
    path('concept-assessment/<int:assessment_id>/teacher-review/', views.teacher_review_view, name='teacher_review'),

    # Sign to English Recognition & Translation Feature
    path('sign-to-english/', views.sign_to_english_view, name='sign_to_english'),
    path('api/sign-to-english/predict-auto/', views.sign_to_english_predict_auto_api, name='sign_to_english_predict_auto_api'),
    path('api/sign-to-english/predict-live/', views.sign_to_english_live_api, name='sign_to_english_live_api'),
    path('api/sign-to-english/predict-alphabet/', views.sign_to_english_predict_alphabet_api, name='sign_to_english_predict_alphabet_api'),
    path('api/sign-to-english/suggest-word/', views.sign_to_english_suggest_word_api, name='sign_to_english_suggest_word_api'),
    path('api/sign-to-english/translate-tokens/', views.sign_to_english_translate_api, name='sign_to_english_translate_api'),
    path('api/sign-to-english/process-video/', views.sign_to_english_video_api, name='sign_to_english_video_api'),
    path('api/sign-to-english/status/', views.sign_to_english_status_api, name='sign_to_english_status_api'),
]


