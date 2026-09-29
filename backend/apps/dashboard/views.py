"""
Dashboard Feature Views
=======================
Central user analytics, uploaded history, streak tracking, and course progress display.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from study_companion.models import PPTUpload, UserProfile, QuizResult
from study_companion.course_data import get_user_course_progress


@login_required(login_url="login")
def dashboard_view(request):
    """
    Main user dashboard displaying learning metrics, streak, vocabulary mastery,
    and recent activity.
    """
    uploads = PPTUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    results = QuizResult.objects.filter(user=request.user)
    total_score = results.aggregate(Sum('score'))['score__sum'] or 0
    total_possible = results.aggregate(Sum('total'))['total__sum'] or 0

    vocab_mastery = 0
    if total_possible > 0:
        vocab_mastery = int((total_score / total_possible) * 100)

    learn_progress = get_user_course_progress(request.user)

    context = {
        'uploads': uploads,
        'streak': profile.current_streak,
        'xp': profile.total_xp,
        'vocab_mastery': vocab_mastery,
        'quiz_count': results.count(),
        'learn_progress': learn_progress
    }

    return render(request, 'dashboard.html', context)


@login_required(login_url="login")
def history_view(request):
    """Lists past uploaded documents, summaries, and assessments."""
    uploads = PPTUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'history.html', {'uploads': uploads})
