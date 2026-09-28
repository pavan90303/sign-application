"""
Learning Feature Views
======================
Handles Indian Sign Language curriculum, sections, lesson walkthroughs,
completion progress, and interactive sign practice.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from study_companion.models import (
    CourseSection,
    Lesson,
    LessonProgress,
    SectionProgress,
    PracticeAttempt
)
from study_companion.course_data import get_user_course_progress
from study_companion.sign_recognition import (
    analyze_practice_sign,
    lookup_sign_for_practice,
    SUPPORTED_RECOGNITION_SIGNS
)


@login_required(login_url="login")
def learn_course_dashboard(request):
    """
    Main Learn Sign Language course dashboard:
    Displays course progress, 5 sections with unlock states, and continue learning action.
    """
    progress_data = get_user_course_progress(request.user)
    return render(request, 'learn_dashboard.html', {
        'progress': progress_data,
        **progress_data
    })


@login_required(login_url="login")
def learn_section_view(request, section_id):
    """
    Section Learning Content & Curriculum Hub.
    Presents a cohesive section-level learning overview and vocabulary items.
    """
    section = get_object_or_404(CourseSection, id=section_id)
    progress_data = get_user_course_progress(request.user)

    sec_info = next((s for s in progress_data['sections'] if s['section'].id == section.id), None)
    if sec_info and not sec_info['is_unlocked']:
        return redirect('learn_dashboard')

    curriculum = []
    for s_info in progress_data['sections']:
        s = s_info['section']
        curriculum.append({
            'section': s,
            'is_current': s.id == section.id,
            'is_unlocked': s_info['is_unlocked'],
            'is_completed': s_info['is_completed'],
            'quiz_passed': s_info['quiz_passed'],
            'best_score': s_info['best_score'],
        })

    lessons = list(section.lessons.all().order_by('order'))
    vocab_items = []
    for l in lessons:
        first_asset = l.sign_asset_list[0] if l.sign_asset_list else None
        vocab_items.append({
            'title': l.title,
            'word_or_phrase': l.word_or_phrase,
            'explanation': l.explanation,
            'learning_type': l.learning_type,
            'has_video': first_asset['exists'] if first_asset else False,
            'video_url': first_asset['url'] if first_asset else '',
        })

    sec_prog = SectionProgress.objects.filter(user=request.user, section=section).first()
    quiz_passed = sec_prog.quiz_completed if sec_prog else False
    best_score = sec_prog.best_score if sec_prog else 0

    next_section = CourseSection.objects.filter(
        course=section.course,
        section_number=section.section_number + 1
    ).first()

    return render(request, 'learn_section.html', {
        'section': section,
        'course': section.course,
        'sec_info': sec_info,
        'curriculum': curriculum,
        'sidebar_sections': curriculum,
        'vocab_items': vocab_items,
        'total_vocab': len(vocab_items),
        'quiz_passed': quiz_passed,
        'best_score': best_score,
        'next_section': next_section,
        'progress': progress_data,
    })


@login_required(login_url="login")
def learn_lesson_view(request, lesson_id):
    """
    Structured lesson interface:
    Left: Course curriculum with sections and lessons
    Right/Main: Lesson title, video player, explanation, mark complete, previous/next
    """
    lesson = get_object_or_404(Lesson, id=lesson_id)
    section = lesson.section
    progress_data = get_user_course_progress(request.user)

    sec_info = next((s for s in progress_data['sections'] if s['section'].id == section.id), None)
    if sec_info and not sec_info['is_unlocked']:
        return redirect('learn_dashboard')

    is_completed = LessonProgress.objects.filter(user=request.user, lesson=lesson, completed=True).exists()

    sec_lessons = list(section.lessons.all().order_by('order'))
    current_idx = next((i for i, l in enumerate(sec_lessons) if l.id == lesson.id), 0)
    prev_lesson = sec_lessons[current_idx - 1] if current_idx > 0 else None
    next_lesson = sec_lessons[current_idx + 1] if current_idx < len(sec_lessons) - 1 else None
    is_last_in_section = (current_idx == len(sec_lessons) - 1)

    completed_lesson_ids = set(LessonProgress.objects.filter(user=request.user, completed=True).values_list('lesson_id', flat=True))

    curriculum = []
    for s_info in progress_data['sections']:
        s = s_info['section']
        lessons_with_status = []
        for l in s.lessons.all().order_by('order'):
            lessons_with_status.append({
                'lesson': l,
                'is_completed': l.id in completed_lesson_ids,
                'is_current': l.id == lesson.id,
            })
        curriculum.append({
            'section': s,
            'info': s_info,
            'lessons': lessons_with_status
        })

    video_exists = False
    video_url = None
    if lesson.sign_asset_list:
        first_asset = lesson.sign_asset_list[0]
        video_exists = first_asset['exists']
        video_url = first_asset['url']

    context = {
        'lesson': lesson,
        'section': section,
        'course': section.course,
        'is_completed': is_completed,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'is_last_in_section': is_last_in_section,
        'curriculum': curriculum,
        'sidebar_sections': curriculum,
        'overall_percentage': progress_data['overall_percentage'],
        'sign_assets': lesson.sign_asset_list,
        'video_exists': video_exists,
        'video_url': video_url,
    }
    return render(request, 'learn_lesson.html', context)


@login_required(login_url="login")
def learn_complete_lesson_api(request, lesson_id):
    """AJAX endpoint: Marks lesson as complete, awards XP, and returns next step."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    lesson = get_object_or_404(Lesson, id=lesson_id)
    prog, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    if not prog.completed:
        prog.completed = True
        prog.save()
        if hasattr(request.user, 'userprofile'):
            request.user.userprofile.total_xp += 5
            request.user.userprofile.save(update_fields=['total_xp'])

    sec_lessons = list(lesson.section.lessons.all().order_by('order'))
    completed_ids = set(LessonProgress.objects.filter(user=request.user, completed=True).values_list('lesson_id', flat=True))
    all_done = all(l.id in completed_ids for l in sec_lessons)

    current_idx = next((i for i, l in enumerate(sec_lessons) if l.id == lesson.id), 0)
    next_lesson = sec_lessons[current_idx + 1] if current_idx < len(sec_lessons) - 1 else None

    return JsonResponse({
        'status': 'ok',
        'is_completed': True,
        'lesson_id': lesson.id,
        'section_completed': all_done,
        'has_next': bool(next_lesson),
        'next_lesson_id': next_lesson.id if next_lesson else None,
        'section_id': lesson.section.id
    })


@login_required(login_url="login")
def learn_section_completed_view(request, section_id):
    """Celebration & decision screen: All lessons in section completed."""
    section = get_object_or_404(CourseSection, id=section_id)
    total_lessons = section.lessons.count()
    completed_lessons = LessonProgress.objects.filter(
        user=request.user,
        lesson__section=section,
        completed=True
    ).count()

    next_section = CourseSection.objects.filter(
        course=section.course,
        section_number=section.section_number + 1
    ).first()

    sec_prog = SectionProgress.objects.filter(user=request.user, section=section).first()
    quiz_passed = sec_prog.quiz_completed if sec_prog else False

    return render(request, 'learn_section_completed.html', {
        'section': section,
        'course': section.course,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'next_section': next_section,
        'quiz_passed': quiz_passed,
    })


@login_required(login_url="login")
def learn_practice_view(request, section_id):
    """Interactive webcam practice arena with side-by-side video and MediaPipe guidance."""
    section = get_object_or_404(CourseSection, id=section_id)
    lessons = list(section.lessons.all().order_by('order'))
    available_signs = [l.word_or_phrase for l in lessons]

    default_lesson = next((l for l in lessons if l.has_sign_asset), lessons[0] if lessons else None)
    initial_video_url = None
    initial_video_exists = False
    if default_lesson and default_lesson.sign_asset_list:
        first_asset = default_lesson.sign_asset_list[0]
        initial_video_exists = first_asset['exists']
        initial_video_url = first_asset['url']

    decorated_lessons = []
    for l in lessons:
        norm = l.word_or_phrase.strip().lower()
        is_supported = norm in SUPPORTED_RECOGNITION_SIGNS or norm.replace(" ", "_") in SUPPORTED_RECOGNITION_SIGNS
        first_a = l.sign_asset_list[0] if l.sign_asset_list else None
        decorated_lessons.append({
            'id': l.id,
            'title': l.title,
            'word_or_phrase': l.word_or_phrase,
            'explanation': l.explanation,
            'is_supported': is_supported,
            'video_url': first_a['url'] if first_a else '',
            'has_video': first_a['exists'] if first_a else False,
        })

    recent_attempts = PracticeAttempt.objects.filter(
        user=request.user, section=section
    ).order_by('-created_at')[:6]

    return render(request, 'learn_practice.html', {
        'section': section,
        'course': section.course,
        'lessons': decorated_lessons,
        'available_signs': available_signs,
        'initial_lesson': default_lesson,
        'default_lesson': default_lesson,
        'initial_video_url': initial_video_url,
        'initial_video_exists': initial_video_exists,
        'recent_attempts': recent_attempts,
        'supported_signs_count': sum(1 for d in decorated_lessons if d['is_supported']),
    })


@login_required(login_url="login")
def learn_practice_lookup_api(request, section_id):
    """API endpoint: Validates sign query against current section vocabulary."""
    query = request.GET.get('q', '').strip()
    result = lookup_sign_for_practice(section_id, query)
    return JsonResponse(result)


@login_required(login_url="login")
def learn_practice_search_api(request, section_id):
    """Search autocomplete within current section."""
    query = request.GET.get('q', '').strip()
    result = lookup_sign_for_practice(section_id, query)
    return JsonResponse(result)


@login_required(login_url="login")
def learn_practice_analyze_api(request, section_id):
    """POST endpoint: Analyzes recorded webcam hand landmark sequence for practice."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        expected_sign = data.get('expected_sign', '')
        frames = data.get('frames', [])
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON payload: {str(e)}'}, status=400)

    result = analyze_practice_sign(section_id, expected_sign, frames, user=request.user)
    return JsonResponse(result)


@login_required(login_url="login")
def learn_practice_attempts_api(request, section_id):
    """Returns user's recent practice attempts for this section."""
    section = get_object_or_404(CourseSection, id=section_id)
    attempts = PracticeAttempt.objects.filter(user=request.user, section=section).order_by('-created_at')[:10]
    data = [{
        'id': a.id,
        'expected_sign': a.expected_sign,
        'predicted_sign': a.predicted_sign,
        'confidence': int(round(a.recognition_confidence * 100)),
        'similarity': int(round(a.reference_similarity * 100)) if a.reference_similarity is not None else None,
        'matched': a.matched,
        'status': a.status,
        'date': a.created_at.strftime('%H:%M, %d %b')
    } for a in attempts]
    return JsonResponse({'status': 'ok', 'attempts': data})
