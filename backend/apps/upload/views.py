"""
Upload Feature Views
====================
Handles presentation and educational document uploads (PPTX, PDF, DOCX, TXT),
text extraction, AI summarization, and sign video breakdown.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from study_companion.models import PPTUpload
from .services.document_extractor import extract_text_from_file
from .services.summarizer import summarize_text
from shared.utils.validators import validate_document_file


@login_required(login_url="login")
def upload_ppt_view(request):
    """Handles file upload, text extraction, and automated summary generation."""
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        is_valid, err_msg = validate_document_file(uploaded_file)
        if not is_valid:
            return render(request, 'upload_ppt.html', {'error': err_msg})

        upload = PPTUpload.objects.create(
            user=request.user,
            file=uploaded_file,
            title=uploaded_file.name
        )

        try:
            text = extract_text_from_file(upload.file.path)
            upload.extracted_text = text

            summary = summarize_text(text)
            upload.summary_text = summary

            upload.save()
            return redirect('summary', session_id=upload.id)
        except Exception as e:
            return render(request, 'upload_ppt.html', {'error': f'Error processing file: {e}'})

    return render(request, 'upload_ppt.html')


@login_required(login_url="login")
def summary_view(request, session_id):
    """Displays structured summary, key concepts, and sign language animation mappings."""
    upload = get_object_or_404(PPTUpload, id=session_id, user=request.user)

    from study_companion.ai_services import process_text_for_sign_language

    try:
        summary_data = json.loads(upload.summary_text)
        if not isinstance(summary_data, dict):
            raise ValueError("Not a dictionary")
        summary_text_content = summary_data.get('summary', '')
    except (json.JSONDecodeError, ValueError, TypeError):
        summary_text_content = upload.summary_text or ""
        summary_data = {
            "summary": summary_text_content,
            "key_concepts": [],
            "important_terms": []
        }

    try:
        sign_words = process_text_for_sign_language(summary_text_content)
    except Exception as e:
        sign_words = []

    return render(request, 'summary.html', {
        'upload': upload,
        'words': sign_words,
        'summary_data': summary_data
    })
