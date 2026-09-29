"""
Shared Gemini Service
=====================
Authoritative Gemini client and API wrapper for SignAI Pro.
Provides centralized API configuration, error handling, rate limiting protection,
and fallback handling.
"""

import os
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def get_gemini_client():
    """
    Returns the configured google.generativeai module if API key is valid,
    or None if unavailable.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
    if not api_key or api_key == 'PLACEHOLDER_KEY':
        logger.warning("GEMINI_API_KEY not configured or is PLACEHOLDER_KEY. Falling back to local generation.")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except ImportError:
        logger.error("google.generativeai package is not installed.")
        return None


def call_gemini_model(prompt, model_name='gemini-1.5-flash', system_instruction=None, json_mode=False):
    """
    Executes a structured text/JSON generation call using Gemini API.
    Returns response text or None if API fails.
    """
    genai = get_gemini_client()
    if not genai:
        return None

    try:
        config = {}
        if json_mode:
            config['response_mime_type'] = 'application/json'

        generation_config = genai.types.GenerationConfig(**config) if config else None

        model_kwargs = {'model_name': model_name}
        if system_instruction:
            model_kwargs['system_instruction'] = system_instruction

        model = genai.GenerativeModel(**model_kwargs)
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if response and hasattr(response, 'text'):
            return response.text
        return None
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None
