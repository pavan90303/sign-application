"""
English Builder Service
=======================
Transforms recognized sign tokens into grammatical, natural English sentences.
"""

from shared.sign_language.sign_recognition_service import SignRecognitionService


def tokens_to_natural_english(tokens: list, use_llm_if_available: bool = True) -> dict:
    """Translates sign tokens into natural English using rule-based grammar and Gemini polish."""
    return SignRecognitionService.tokens_to_english(tokens, use_llm_if_available=use_llm_if_available)
