"""
Transcript Processor Service
============================
Transforms raw recognized sign tokens into a coherent, natural English explanation
grounded in the student's actual performance.
"""

import json
import logging
from shared.ai.gemini_service import get_gemini_client
from shared.sign_language.sign_recognition_service import SignRecognitionService

logger = logging.getLogger(__name__)


def reconstruct_isl_sequence_to_meaning(raw_units: list, topic: str = "") -> str:
    """
    Converts raw recognized ISL sign units into a natural, grammatically coherent English explanation.
    """
    if not raw_units:
        return "No clear sign explanation recognized."

    cleaned_units = [str(u).strip().upper() for u in raw_units if str(u).strip()]
    if not cleaned_units:
        return "No clear sign explanation recognized."

    # Use shared SignRecognitionService rule translation first
    rule_res = SignRecognitionService.tokens_to_english(cleaned_units, use_llm_if_available=False)
    rule_text = rule_res.get('english', '')

    client = get_gemini_client()
    if client:
        prompt = f"""Convert the following recognized Indian Sign Language (ISL) sign sequence into a clear, natural English sentence.
Context topic: {topic if topic else 'General Science/Education'}

Recognized ISL Sign Units: {json.dumps(cleaned_units)}

ISL uses topic-comment structure. Reconstruct the exact intended meaning in grammatical English.
Return ONLY the single reconstructed English sentence.
"""
        for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash']:
            try:
                model = client.GenerativeModel(model_name)
                res = model.generate_content(prompt)
                if res and res.text:
                    out_text = res.text.strip().strip('"').strip("'")
                    if out_text:
                        return out_text
            except Exception as e:
                logger.debug(f"[ConceptAssessment] Reconstruction fallback warning ({model_name}): {e}")

    if rule_text and len(rule_text) > 3:
        return rule_text

    phrase = " ".join([u.capitalize() for u in cleaned_units])
    return f"We interpreted your sign explanation as: {phrase}."
