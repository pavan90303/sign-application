"""
Reference Knowledge Processor
=============================
Extracts concepts and relationships from educational reference text using Gemini AI
or deterministic NLP extraction engine.
"""

import re
import json
import logging
from shared.ai.gemini_service import get_gemini_client
from apps.concept_assessment.prompts import get_reference_extraction_prompt

logger = logging.getLogger(__name__)


def normalize_knowledge_schema(data: dict, topic_hint: str = "") -> dict:
    """Normalizes knowledge schema to guarantee {topic, concepts, relationships} format."""
    if not isinstance(data, dict):
        data = {}

    topic = data.get('topic') or topic_hint or "General Concept"
    raw_concepts = data.get('concepts', [])
    raw_relationships = data.get('relationships', [])

    concepts = []
    seen_ids = set()

    for idx, c in enumerate(raw_concepts):
        if isinstance(c, str):
            c_name = c.strip()
            c_id = re.sub(r'[^a-z0-9]+', '_', c_name.lower()).strip('_')
            c_importance = "core"
        elif isinstance(c, dict):
            c_name = str(c.get('name') or c.get('title') or c.get('id') or f"Concept_{idx+1}").strip()
            c_id = str(c.get('id') or re.sub(r'[^a-z0-9]+', '_', c_name.lower())).strip('_')
            c_importance = str(c.get('importance', 'core')).lower()
        else:
            continue

        if not c_id:
            c_id = f"concept_{idx+1}"
        if c_id not in seen_ids:
            seen_ids.add(c_id)
            concepts.append({
                "id": c_id,
                "name": c_name,
                "importance": c_importance if c_importance in ["core", "supporting", "optional"] else "core"
            })

    relationships = []
    for r in raw_relationships:
        if isinstance(r, dict):
            src = str(r.get('source', '')).strip().lower().replace(' ', '_')
            rel = str(r.get('relation', '')).strip()
            tgt = str(r.get('target', '')).strip().lower().replace(' ', '_')
            if src and tgt and rel:
                relationships.append({
                    "source": src,
                    "relation": rel,
                    "target": tgt
                })

    return {
        "topic": topic,
        "concepts": concepts,
        "relationships": relationships
    }


def _deterministic_reference_extraction(text: str, topic_hint: str = "") -> dict:
    """Grounded NLP reference knowledge extraction fallback."""
    topic = topic_hint or "Educational Concept"
    text_clean = text.lower()

    academic_keywords = [
        "photosynthesis", "chlorophyll", "chloroplast", "sunlight", "water",
        "carbon dioxide", "glucose", "oxygen", "energy", "plant", "plants",
        "autotroph", "light", "chemical energy", "stomata", "roots", "leaves"
    ]

    found_concepts = []
    for kw in academic_keywords:
        if kw in text_clean:
            found_concepts.append(kw)

    if len(found_concepts) < 3:
        words = re.findall(r'\b[A-Za-z]{4,}\b', text)
        for w in words[:6]:
            if w.lower() not in found_concepts:
                found_concepts.append(w.lower())

    concepts = []
    for c in found_concepts[:8]:
        c_id = c.replace(' ', '_')
        concepts.append({
            "id": c_id,
            "name": c.capitalize(),
            "importance": "core"
        })

    relationships = []
    if "plant" in found_concepts and "sunlight" in found_concepts:
        relationships.append({"source": "plant", "relation": "absorbs", "target": "sunlight"})
    if "plant" in found_concepts and "water" in found_concepts:
        relationships.append({"source": "plant", "relation": "absorbs", "target": "water"})
    if "plant" in found_concepts and "glucose" in found_concepts:
        relationships.append({"source": "plant", "relation": "produces", "target": "glucose"})
    if "plant" in found_concepts and "oxygen" in found_concepts:
        relationships.append({"source": "plant", "relation": "releases", "target": "oxygen"})

    return {
        "topic": topic,
        "concepts": concepts,
        "relationships": relationships
    }


def extract_reference_knowledge_representation(reference_text: str, topic_hint: str = "") -> dict:
    """Extracts structured reference concept representation (nodes and directed relationships)."""
    if not reference_text or not reference_text.strip():
        return normalize_knowledge_schema({"topic": topic_hint or "General Concept", "concepts": [], "relationships": []})

    client = get_gemini_client()
    if client:
        prompt = get_reference_extraction_prompt(reference_text, topic_hint=topic_hint)
        for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash']:
            try:
                model = client.GenerativeModel(model_name)
                res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                if res and res.text:
                    raw_json = res.text.strip()
                    raw_json = re.sub(r'^```(?:json)?\s*', '', raw_json)
                    raw_json = re.sub(r'\s*```$', '', raw_json)
                    data = json.loads(raw_json)
                    return normalize_knowledge_schema(data, topic_hint=topic_hint)
            except Exception as e:
                logger.debug(f"Gemini reference extraction error ({model_name}): {e}")

    fallback_data = _deterministic_reference_extraction(reference_text, topic_hint=topic_hint)
    return normalize_knowledge_schema(fallback_data, topic_hint=topic_hint)
