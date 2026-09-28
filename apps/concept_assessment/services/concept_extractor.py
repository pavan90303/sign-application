"""
Concept Extractor Service
=========================
Extracts knowledge concepts and relationships from the student's reconstructed sign explanation.
"""

import re
import json
import logging
from shared.ai.gemini_service import get_gemini_client

logger = logging.getLogger(__name__)


def extract_student_knowledge_representation(reconstructed_text: str, topic: str = "") -> dict:
    """Extracts concepts and relationships present in the student's reconstructed explanation."""
    if not reconstructed_text or not reconstructed_text.strip():
        return {"concepts": [], "relationships": []}

    client = get_gemini_client()
    if client:
        prompt = f"""Analyze the student's explanation and extract a structured knowledge representation JSON.
Topic: {topic}

Student Explanation:
\"\"\"{reconstructed_text}\"\"\"

Return ONLY a single valid JSON object:
{{
  "concepts": ["concept1", "concept2"],
  "relationships": [
    {{
      "source": "concept1",
      "relation": "action",
      "target": "concept2"
    }}
  ]
}}
"""
        for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash']:
            try:
                model = client.GenerativeModel(model_name)
                res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                if res and res.text:
                    raw_json = res.text.strip()
                    raw_json = re.sub(r'^```(?:json)?\s*', '', raw_json)
                    raw_json = re.sub(r'\s*```$', '', raw_json)
                    return json.loads(raw_json)
            except Exception as e:
                logger.debug(f"[ConceptAssessment] Student extraction warning ({model_name}): {e}")

    words = re.findall(r'\b[a-zA-Z]{3,}\b', reconstructed_text.lower())
    stop_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was', 'were', 'have', 'has', 'had', 'been', 'which', 'using', 'into', 'used', 'can', 'may', 'process', 'by', 'such', 'interpreted', 'your', 'explanation'}
    student_concepts = list(set([w for w in words if w not in stop_words]))

    rels = []
    if len(student_concepts) >= 2:
        rels.append({"source": student_concepts[0], "relation": "uses", "target": student_concepts[1]})

    return {
        "concepts": student_concepts,
        "relationships": rels
    }
