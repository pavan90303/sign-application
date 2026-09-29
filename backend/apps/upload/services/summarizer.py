"""
Upload Summarizer Service
=========================
Summarizes presentation/document text into executive summary, key concepts,
and sign vocabulary terms using Gemini or document-based structured fallback.
"""

import re
import json
import logging
from shared.ai.gemini_service import get_gemini_client

logger = logging.getLogger(__name__)


def summarize_text(text: str) -> str:
    """
    Summarizes the given text using Gemini (or structured document analysis fallback).
    Returns a JSON string with structured data.
    """
    if not text or len(text.strip()) < 50:
        return json.dumps({
            "summary": "Document content is too brief for an extended summary.",
            "key_concepts": [],
            "important_terms": []
        })

    client = get_gemini_client()
    if client:
        prompt = f"""Analyze the following presentation content and provide a structured learning summary in valid JSON.

Return a JSON object with:
1. "summary": A concise executive summary paragraph (approx 3-5 sentences).
2. "key_concepts": Array of 3-5 items each with "title", "description", and "color" ("green", "blue", or "purple").
3. "important_terms": Array of specific nouns/verbs crucial for sign language practice.

Content:
{text[:10000]}
"""
        for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash']:
            try:
                model = client.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.debug(f"Summary Generation Error ({model_name}): {e}")

    # Document-based structured summary fallback
    first_paras = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30 and not p.strip().startswith('---')]
    summary_para = " ".join(first_paras[:2])[:400] if first_paras else text[:300]
    words = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', text)
    terms = list(dict.fromkeys([w for w in words if w.lower() not in ['slide', 'title', 'thank', 'author']]))[:8]
    colors = ["green", "blue", "purple"]
    key_concepts = []
    for i, t in enumerate(terms[:4]):
        key_concepts.append({
            "title": t,
            "description": f"Key educational concept highlighted in the document.",
            "color": colors[i % len(colors)]
        })

    return json.dumps({
        "summary": summary_para,
        "key_concepts": key_concepts,
        "important_terms": terms
    })
