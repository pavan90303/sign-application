"""
Live Converter Feature Views
============================
Converts spoken English / text into synchronized Indian Sign Language (ISL) animations.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services.nlp_processor import process_text_to_sign_words


@login_required(login_url="login")
def animation_view(request):
    """
    Renders the live text/speech-to-sign converter.
    When a sentence is submitted via POST, extracts lemma sequence and maps each token
    to corresponding video asset or fingerspelling sequence.
    """
    if request.method == 'POST':
        text = request.POST.get('sen', '')
        words = process_text_to_sign_words(text)
        return render(request, 'animation.html', {'words': words, 'text': text})
    else:
        return render(request, 'animation.html')
