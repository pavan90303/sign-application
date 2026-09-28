"""
Concept Assessment Feature Views
================================
Handles uploading student sign video explanations, reference concept extraction,
semantic concept alignment, gap analysis, and teacher inspection review.
Reuses the authoritative shared SignRecognitionService.
"""

import os
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from study_companion.models import (
    CourseSection,
    ConceptAssessment,
    ConceptResult,
    AssessmentAttempt,
    TeacherReview
)
from apps.concept_assessment.services.reference_processor import extract_reference_knowledge_representation
from apps.concept_assessment.services.transcript_processor import reconstruct_isl_sequence_to_meaning
from apps.concept_assessment.services.concept_extractor import extract_student_knowledge_representation
from apps.concept_assessment.services.concept_comparator import perform_semantic_concept_comparison
from apps.concept_assessment.services.video_processor import process_student_explanation_video
from apps.upload.services.document_extractor import extract_text_from_file
from shared.utils.validators import validate_video_file

logger = logging.getLogger(__name__)


@login_required(login_url="login")
def concept_assessment_view(request):
    """Main Concept Assessment interface."""
    sections = CourseSection.objects.all().order_by('section_number')
    recent_assessments = ConceptAssessment.objects.filter(user=request.user).order_by('-created_at')[:5]

    return render(request, 'concept_assessment.html', {
        'sections': sections,
        'recent_assessments': recent_assessments,
    })


@login_required(login_url="login")
def concept_assessment_save_reference_api(request):
    """POST API: Accepts reference text, uploaded PDF/PPT file, or course section selection."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        source_type = request.POST.get('source_type', 'text').strip().lower()
        topic = request.POST.get('topic', '').strip()
        reference_text = ""

        if source_type == 'file':
            if 'file' not in request.FILES or not request.FILES['file'].name:
                return JsonResponse({'status': 'error', 'message': 'Please select a PDF or PPT file to upload.'}, status=400)
            uploaded_file = request.FILES['file']
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'concept_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            reference_text = extract_text_from_file(file_path)
            if not reference_text or not reference_text.strip():
                return JsonResponse({'status': 'error', 'message': 'No readable text could be extracted from the uploaded document.'}, status=400)
            if not topic:
                topic = os.path.splitext(uploaded_file.name)[0].replace('_', ' ').title()

        elif source_type == 'course':
            section_id = request.POST.get('section_id')
            if not section_id:
                return JsonResponse({'status': 'error', 'message': 'Please select a course section.'}, status=400)
            sec = CourseSection.objects.filter(id=section_id).first()
            if not sec:
                return JsonResponse({'status': 'error', 'message': 'Selected course section not found.'}, status=400)
            lessons_text = "\n".join([f"{l.title}: {l.explanation}" for l in sec.lessons.all()])
            reference_text = f"Section {sec.section_number}: {sec.title}\n{sec.description}\n\nKey Concepts:\n{lessons_text}"
            topic = sec.title

        else:
            source_type = 'text'
            reference_text = request.POST.get('reference_text', '').strip()
            if not reference_text:
                return JsonResponse({'status': 'error', 'message': 'Please enter reference concept text.'}, status=400)
            if not topic:
                topic = "General Concept"

        ref_rep = extract_reference_knowledge_representation(reference_text, topic_hint=topic)

        return JsonResponse({
            'status': 'ok',
            'topic': ref_rep.get('topic', topic),
            'reference_text': reference_text,
            'source_type': source_type,
            'reference_source': source_type,
            'reference_concepts_json': ref_rep
        })

    except Exception as e:
        logger.exception("Reference concept processing failed")
        err_msg = f"Reference processing failed: {str(e)}" if settings.DEBUG else "Reference processing failed."
        return JsonResponse({'status': 'error', 'message': err_msg}, status=500)


@login_required(login_url="login")
def concept_assessment_analyze_api(request):
    """
    POST API: Evaluates student's sign language explanation video.
    Uses shared SignRecognitionService to decode MP4, track landmarks,
    and generate English transcript without leakage of reference text.
    """
    # Delegate to study_companion's battle-tested analyze endpoint or call directly
    from study_companion.views import concept_assessment_analyze_api as original_analyze_api
    return original_analyze_api(request)


@login_required(login_url="login")
def concept_assessment_relearn_api(request, concept_name):
    """Returns targeted micro-lesson and visual sign guide for missing/weak concepts."""
    c_lower = str(concept_name).strip().lower()

    explanations = {
        "carbon dioxide": {
            "title": "Role of Carbon Dioxide in Photosynthesis",
            "explanation": "Carbon dioxide (CO₂) enters plants through small pores in their leaves called stomata. Plants combine carbon dioxide with water using solar energy from sunlight to synthesize glucose and release fresh oxygen into the air.",
            "isl_sign_name": "Carbon Dioxide",
            "isl_sign_asset": "C.mp4",
            "key_takeaway": "Plants absorb carbon dioxide from the air to make food."
        },
        "glucose": {
            "title": "Understanding Glucose as Plant Energy",
            "explanation": "Glucose is the simple sugar produced by plants during photosynthesis. It acts as their primary food source, providing energy for plant growth, flowering, and cellular repair.",
            "isl_sign_name": "Glucose / Food",
            "isl_sign_asset": "Food.mp4",
            "key_takeaway": "Glucose is the sugar energy created by plants."
        },
        "sunlight": {
            "title": "Sunlight as the Energy Catalyst",
            "explanation": "Sunlight provides the essential light energy that powers the chemical conversion of water and carbon dioxide into glucose. Chlorophyll in leaves absorbs this solar energy.",
            "isl_sign_name": "Sunlight / Light",
            "isl_sign_asset": "Sun.mp4",
            "key_takeaway": "Sunlight powers the entire food-making process."
        },
        "water": {
            "title": "Water Transport in Plants",
            "explanation": "Roots absorb water (H₂O) from the soil and transport it up through the stem to the leaves, where it reacts with carbon dioxide.",
            "isl_sign_name": "Water",
            "isl_sign_asset": "Water.mp4",
            "key_takeaway": "Roots draw water from the soil for photosynthesis."
        }
    }

    info = explanations.get(c_lower, {
        "title": f"Learning {concept_name.capitalize()}",
        "explanation": f"Review the essential definition and relationship of {concept_name} in your reference study material.",
        "isl_sign_name": concept_name.capitalize(),
        "isl_sign_asset": "A.mp4",
        "key_takeaway": f"Understand how {concept_name} interacts with other core concepts."
    })

    return JsonResponse({'status': 'ok', 'relearn_data': info})


@login_required(login_url="login")
def concept_assessment_history_api(request):
    """Returns user's recent assessment history and attempt progression."""
    topic = request.GET.get('topic')
    qs = ConceptAssessment.objects.filter(user=request.user)
    if topic:
        qs = qs.filter(topic=topic)

    assessments = qs.order_by('-created_at')[:10]
    data = [{
        'id': a.id,
        'topic': a.topic,
        'explanation_source': a.explanation_source,
        'recognition_confidence_pct': int(round(a.recognition_confidence * 100)),
        'concept_coverage_pct': int(round(a.concept_coverage * 100)),
        'relationship_accuracy_pct': int(round(a.relationship_accuracy * 100)),
        'overall_score_pct': int(round(a.overall_understanding_score * 100)),
        'reconstructed_explanation': a.reconstructed_explanation,
        'date': a.created_at.strftime('%H:%M, %d %b %Y')
    } for a in assessments]

    return JsonResponse({'status': 'ok', 'history': data})


@login_required(login_url="login")
def teacher_review_view(request, assessment_id):
    """Teacher Inspection & Verification View."""
    assessment = get_object_or_404(ConceptAssessment, id=assessment_id)
    review = TeacherReview.objects.filter(assessment=assessment).first()

    if request.method == 'POST':
        corrected_reconstruction = request.POST.get('corrected_reconstruction')
        corrected_coverage = request.POST.get('corrected_coverage')
        corrected_relationship_accuracy = request.POST.get('corrected_relationship_accuracy')
        teacher_notes = request.POST.get('teacher_notes')

        cov_val = float(corrected_coverage) / 100.0 if corrected_coverage else assessment.concept_coverage
        rel_val = float(corrected_relationship_accuracy) / 100.0 if corrected_relationship_accuracy else assessment.relationship_accuracy

        if not review:
            review = TeacherReview.objects.create(
                assessment=assessment,
                teacher=request.user,
                is_verified=True,
                corrected_reconstruction=corrected_reconstruction,
                corrected_coverage=cov_val,
                corrected_relationship_accuracy=rel_val,
                teacher_notes=teacher_notes
            )
        else:
            review.teacher = request.user
            review.is_verified = True
            review.corrected_reconstruction = corrected_reconstruction
            review.corrected_coverage = cov_val
            review.corrected_relationship_accuracy = rel_val
            review.teacher_notes = teacher_notes
            review.save()

        messages.success(request, "Teacher verification saved successfully!")
        return redirect('concept_assessment')

    return render(request, 'teacher_review.html', {
        'assessment': assessment,
        'review': review,
    })
