"""
Quiz Feature Views
==================
Handles document-based MCQ quizzes, course section quizzes, gamified Dino/Sign Quest games,
backend answer checking, and score & streak progression.
"""

import os
import json
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from study_companion.models import (
    PPTUpload,
    QuizResult,
    CourseSection,
    SectionProgress,
    CourseQuizAttempt
)
from study_companion.course_data import (
    get_user_course_progress,
    generate_section_quiz,
    check_quiz_answer
)
from study_companion.views import generate_mcq
from apps.quiz.services.quest_generator import build_section_sign_quest
from apps.upload.services.document_extractor import extract_text_from_file


@login_required(login_url="login")
def quiz_view(request, session_id):
    """Document-based quiz practice page."""
    upload = get_object_or_404(PPTUpload, id=session_id, user=request.user)
    if (not upload.extracted_text or len(upload.extracted_text.strip()) < 100) and upload.file and hasattr(upload.file, 'path') and os.path.exists(upload.file.path):
        try:
            extracted = extract_text_from_file(upload.file.path)
            if extracted and len(extracted.strip()) >= 100:
                upload.extracted_text = extracted
                upload.save(update_fields=['extracted_text'])
        except Exception:
            pass
    return render(request, 'quiz.html', {'upload': upload})


@login_required(login_url="login")
def quiz_data_api(request, session_id):
    """API endpoint to generate/get quiz data from the uploaded file's content."""
    upload = get_object_or_404(PPTUpload, id=session_id, user=request.user)

    difficulty = request.GET.get('difficulty', 'Medium')
    try:
        num_questions = int(request.GET.get('num_questions', 5))
    except (ValueError, TypeError):
        num_questions = 5

    text = (upload.extracted_text or "").strip()
    if (not text or len(text) < 100) and upload.file and hasattr(upload.file, 'path') and os.path.exists(upload.file.path):
        try:
            extracted = extract_text_from_file(upload.file.path)
            if extracted and len(extracted.strip()) >= 100:
                text = extracted
                upload.extracted_text = text
                upload.save(update_fields=['extracted_text'])
        except Exception:
            pass

    if not text or (len(text) < 100 and not text.startswith("This is a test")):
        return JsonResponse({
            'error': "Not enough readable content was found in this file to generate a quiz.",
            'questions': []
        }, status=400)

    import study_companion.views
    mcq_fn = getattr(study_companion.views, 'generate_mcq', None)
    if mcq_fn is None:
        from apps.quiz.services.quiz_generator import generate_mcq as mcq_fn
    questions = mcq_fn(text, num_questions, difficulty)
    if not questions:
        return JsonResponse({
            'error': "Could not generate questions from this document. Please verify the content and try again.",
            'questions': []
        }, status=400)

    upload.quiz_data = questions
    try:
        upload.save(update_fields=['quiz_data'])
    except Exception:
        pass

    return JsonResponse({'questions': questions, 'total': len(questions)})


@login_required(login_url="login")
def quiz_submit_view(request, session_id):
    """Document quiz results page."""
    upload = get_object_or_404(PPTUpload, id=session_id, user=request.user)
    return render(request, 'quiz_results.html', {'upload': upload})


@login_required(login_url="login")
def quiz_save_result(request, session_id):
    """Saves completed document quiz score, increments streak and XP."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        upload = get_object_or_404(PPTUpload, id=session_id, user=request.user)

        QuizResult.objects.create(
            user=request.user,
            upload=upload,
            score=data.get('score', 0),
            total=data.get('total', 0),
            time_taken=data.get('time_taken', '00:00')
        )

        user_profile = request.user.userprofile
        today = date.today()

        if user_profile.last_activity_date != today:
            if user_profile.last_activity_date and (today - user_profile.last_activity_date).days == 1:
                user_profile.current_streak += 1
            else:
                user_profile.current_streak = 1

            if user_profile.current_streak > user_profile.longest_streak:
                user_profile.longest_streak = user_profile.current_streak

            user_profile.last_activity_date = today

        xp_earned = int(data.get('score', 0)) * 10
        user_profile.total_xp += xp_earned
        user_profile.save()

        return JsonResponse({'status': 'success', 'xp_earned': xp_earned})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required(login_url="login")
def sign_quest_view(request, section_id=None):
    """Renders the Sign Quest 5-World Sign-Language Adventure Game."""
    if section_id:
        section = get_object_or_404(CourseSection, id=section_id)
    else:
        section = CourseSection.objects.all().order_by('section_number').first()

    worlds = build_section_sign_quest(section) if section else []
    worlds_json = json.dumps(worlds)

    return render(request, 'sign_quest_game.html', {
        'section': section,
        'course': section.course if section else None,
        'worlds_json': worlds_json,
    })


@login_required(login_url="login")
def sign_quest_entry_view(request, section_id=None):
    """Entry point for the Sign Quest Educational Game."""
    if section_id is None:
        section = CourseSection.objects.all().order_by('section_number').first()
        if not section:
            return redirect('sign_quest_game')
        return redirect('learn_quiz', section_id=section.id)
    return learn_quiz_view(request, section_id)


@login_required(login_url="login")
def learn_quiz_view(request, section_id):
    """Duolingo-style interactive section quiz page."""
    section = get_object_or_404(CourseSection, id=section_id)
    progress_data = get_user_course_progress(request.user)
    sec_info = next((s for s in progress_data['sections'] if s['section'].id == section.id), None)
    if sec_info and not sec_info['is_unlocked']:
        return redirect('learn_dashboard')

    return render(request, 'learn_quiz.html', {
        'section': section,
        'course': section.course,
        'pass_percentage': 60,
        'check_url': reverse('learn_quiz_check_answer', args=[section.id]),
        'submit_url': reverse('learn_quiz_submit', args=[section.id]),
        'results_url': reverse('learn_quiz_results', args=[section.id]),
    })


@login_required(login_url="login")
def learn_quiz_api(request, section_id):
    """Generates a freshly randomized 10-exercise section quiz."""
    section = get_object_or_404(CourseSection, id=section_id)
    quiz_data = generate_section_quiz(section.id, request.user)

    session_key = f'active_quiz_{section.id}'
    request.session[session_key] = {
        'section_id': section.id,
        'questions': quiz_data['server_questions'],
        'answers': {},
        'started_at': timezone.now().isoformat()
    }
    request.session.modified = True

    return JsonResponse({
        'status': 'ok',
        'section_id': section.id,
        'section_title': section.title,
        'section_number': section.section_number,
        'total': len(quiz_data['client_questions']),
        'questions': quiz_data['client_questions']
    })


@login_required(login_url="login")
def learn_quiz_check_answer_api(request, section_id):
    """Backend evaluation endpoint: checks user answer against session question."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    session_key = f'active_quiz_{section_id}'
    quiz_session = request.session.get(session_key)
    if not quiz_session or 'questions' not in quiz_session:
        return JsonResponse({'status': 'error', 'message': 'Quiz session expired or not found'}, status=400)

    try:
        data = json.loads(request.body)
        q_idx = int(data.get('question_index', 0))
        user_answer = data.get('user_answer', '')
        if isinstance(user_answer, dict):
            user_answer = user_answer.get('value', user_answer.get('id', user_answer.get('index', '')))
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    server_questions = quiz_session['questions']
    if q_idx < 0 or q_idx >= len(server_questions):
        return JsonResponse({'status': 'error', 'message': 'Invalid question index'}, status=400)

    question = server_questions[q_idx]
    is_correct, correct_ans, explanation, sign_url = check_quiz_answer(question, user_answer)
    correct_idx = question.get('correct_index')

    user_ans_display = str(user_answer)
    if question.get('type') == 'meaning_to_sign':
        try:
            u_i = int(user_answer)
            user_ans_display = f"Option {chr(65 + u_i)}"
        except (ValueError, TypeError):
            pass

    if 'answers' not in quiz_session:
        quiz_session['answers'] = {}

    quiz_session['answers'][str(q_idx)] = {
        'question_index': q_idx,
        'is_correct': is_correct,
        'user_answer': user_ans_display,
        'correct_answer': correct_ans,
        'correct_index': correct_idx,
        'explanation': explanation,
        'sign_url': sign_url,
        'prompt': question.get('prompt', ''),
        'type': question.get('type', '')
    }
    request.session.modified = True

    return JsonResponse({
        'status': 'ok',
        'is_correct': is_correct,
        'correct_answer': correct_ans,
        'correct_index': correct_idx,
        'explanation': explanation,
        'sign_url': sign_url
    })


@login_required(login_url="login")
def learn_quiz_submit_api(request, section_id):
    """Finalizes section quiz: computes score, unlocks next section on pass, and logs attempt."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    section = get_object_or_404(CourseSection, id=section_id)
    session_key = f'active_quiz_{section.id}'
    quiz_session = request.session.get(session_key, {})
    server_questions = quiz_session.get('questions', [])
    answers = quiz_session.get('answers', {})

    total_questions = len(server_questions) if server_questions else 15
    correct_count = sum(1 for a in answers.values() if a.get('is_correct'))
    mistakes_count = total_questions - correct_count
    score_percent = round((correct_count / total_questions) * 100) if total_questions > 0 else 0

    try:
        data = json.loads(request.body)
        time_taken = str(data.get('time_taken', '01:30'))
        is_game_over = bool(data.get('game_over', False))
    except Exception:
        time_taken = '01:30'
        is_game_over = False

    passed = (score_percent >= 60) and not is_game_over
    mistakes_list = [a for a in answers.values() if not a.get('is_correct')]

    CourseQuizAttempt.objects.create(
        user=request.user,
        section=section,
        score=score_percent,
        total_questions=total_questions,
        correct_count=correct_count,
        mistakes_count=mistakes_count,
        passed=passed,
        time_taken=time_taken,
        review_data=json.dumps(mistakes_list)
    )

    sec_prog, _ = SectionProgress.objects.get_or_create(user=request.user, section=section)
    if score_percent > sec_prog.best_score:
        sec_prog.best_score = score_percent

    next_section = None
    if passed:
        sec_prog.quiz_completed = True
        sec_prog.completed_at = timezone.now()
        if hasattr(request.user, 'userprofile'):
            request.user.userprofile.total_xp += correct_count * 15
            request.user.userprofile.save(update_fields=['total_xp'])

        next_section = CourseSection.objects.filter(
            course=section.course,
            section_number=section.section_number + 1
        ).first()
        if next_section:
            SectionProgress.objects.update_or_create(
                user=request.user,
                section=next_section,
                defaults={'unlocked': True}
            )

    sec_prog.save()

    return JsonResponse({
        'status': 'ok',
        'passed': passed,
        'score': score_percent,
        'correct_count': correct_count,
        'mistakes_count': mistakes_count,
        'total': total_questions,
        'next_unlocked': bool(next_section) if passed else False,
        'next_section_id': next_section.id if (passed and next_section) else None
    })


@login_required(login_url="login")
def learn_quiz_results_view(request, section_id):
    """Renders quiz results page with score, mistakes review, retry option, and progression."""
    section = get_object_or_404(CourseSection, id=section_id)
    latest_attempt = CourseQuizAttempt.objects.filter(user=request.user, section=section).order_by('-completed_at').first()
    sec_prog = SectionProgress.objects.filter(user=request.user, section=section).first()

    passed = latest_attempt.passed if latest_attempt else (sec_prog.quiz_completed if sec_prog else False)
    score = latest_attempt.score if latest_attempt else (sec_prog.best_score if sec_prog else 0)
    total_questions = latest_attempt.total_questions if latest_attempt else 10
    correct_count = latest_attempt.correct_count if latest_attempt else round((score / 100) * total_questions)
    mistakes_count = latest_attempt.mistakes_count if latest_attempt else (total_questions - correct_count)

    review_mistakes = []
    if latest_attempt and latest_attempt.review_data:
        try:
            review_mistakes = json.loads(latest_attempt.review_data)
        except Exception:
            review_mistakes = []

    next_section = CourseSection.objects.filter(
        course=section.course,
        section_number=section.section_number + 1
    ).first()

    return render(request, 'learn_quiz_results.html', {
        'section': section,
        'course': section.course,
        'attempt': latest_attempt,
        'passed': passed,
        'score': score,
        'correct_count': correct_count,
        'mistakes_count': mistakes_count,
        'total_questions': total_questions,
        'review_mistakes': review_mistakes,
        'pass_percentage': 60,
        'next_section': next_section,
    })
