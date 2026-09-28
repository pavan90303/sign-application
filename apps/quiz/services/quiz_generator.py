"""
Quiz Generator Service
======================
Generates educational multiple choice questions (MCQs) from document text.
Supports Gemini AI with strict JSON schema validation, and intelligent
document-derived fallback question generation.
"""

import re
import json
import random
import logging
from shared.ai.gemini_service import get_gemini_client
from apps.quiz.prompts import get_mcq_generation_prompt

logger = logging.getLogger(__name__)


def prepare_content_for_quiz(text: str, max_chars: int = 15000) -> str:
    """
    Distributes token budget across the document, prioritizing titles,
    definitions, and bullet points.
    """
    if not text or len(text) <= max_chars:
        return text

    sections = re.split(r'(?=(?:--- Slide|--- Page|\n#{1,3} ))', text)
    if len(sections) <= 1:
        sections = [p.strip() for p in text.split('\n\n') if p.strip()]

    if not sections:
        return text[:max_chars]

    quota_per_sec = max(200, max_chars // min(len(sections), 20))
    selected_parts = []
    current_length = 0

    step = max(1, len(sections) // 20)
    sampled_indices = list(range(0, len(sections), step))
    if (len(sections) - 1) not in sampled_indices:
        sampled_indices.append(len(sections) - 1)

    for idx in sampled_indices:
        sec = sections[idx].strip()
        if not sec:
            continue
        lines = sec.splitlines()
        high_val_lines = []
        regular_lines = []
        for line in lines:
            l_strip = line.strip()
            if not l_strip:
                continue
            if l_strip.startswith(('---', 'Title:', '#', '- ', '* ', '• ')) or any(
                w in l_strip.lower() for w in ['defined', 'means', 'is a', 'refers to', 'purpose', 'key', 'concept', 'component', 'algorithm', 'system', 'method']
            ):
                high_val_lines.append(l_strip)
            else:
                regular_lines.append(l_strip)

        chosen = high_val_lines + regular_lines
        sec_text = "\n".join(chosen)[:quota_per_sec]

        if current_length + len(sec_text) + 2 <= max_chars:
            selected_parts.append(sec_text)
            current_length += len(sec_text) + 2

    return "\n\n".join(selected_parts) if selected_parts else text[:max_chars]


def parse_and_validate_quiz_json(raw_text: str) -> list:
    """
    Parses and strictly validates Gemini response into required schema:
    - Strips markdown code blocks
    - Ensures exactly 4 options, valid correct_answer, and explanation.
    """
    if not raw_text or not raw_text.strip():
        return []

    cleaned = raw_text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```$', '', cleaned)

    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
    if match:
        cleaned = match.group(1)

    try:
        data = json.loads(cleaned)
    except Exception as e:
        logger.debug(f"JSON parsing error: {e}. Raw text snippet: {cleaned[:200]}")
        return []

    raw_questions = []
    if isinstance(data, dict):
        raw_questions = data.get('questions', [])
    elif isinstance(data, list):
        raw_questions = data

    validated = []
    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        q_text = str(item.get('question', '')).strip()
        opts = item.get('options', [])
        corr = item.get('correct_answer') or item.get('answer')
        expl = str(item.get('explanation', '')).strip() or "Based on the uploaded document content."

        if not q_text or not isinstance(opts, list) or len(opts) < 2:
            continue

        clean_opts = [str(o).strip() for o in opts if str(o).strip()]
        while len(clean_opts) < 4:
            clean_opts.append(f"Option {chr(65 + len(clean_opts))}")
        clean_opts = clean_opts[:4]

        correct_answer = ""
        correct_index = 0
        corr_str = str(corr).strip() if corr is not None else ""

        letter_match = re.match(r'^(?:option\s+)?([A-D])$', corr_str, re.IGNORECASE)
        if letter_match:
            correct_index = ord(letter_match.group(1).upper()) - ord('A')
            correct_answer = clean_opts[correct_index]
        elif corr_str.isdigit() and 0 <= int(corr_str) < len(clean_opts):
            correct_index = int(corr_str)
            correct_answer = clean_opts[correct_index]
        else:
            found = False
            for idx, opt in enumerate(clean_opts):
                if opt.lower() == corr_str.lower():
                    correct_answer = opt
                    correct_index = idx
                    found = True
                    break
            if not found:
                for idx, opt in enumerate(clean_opts):
                    if corr_str.lower() in opt.lower() or opt.lower() in corr_str.lower():
                        correct_answer = opt
                        correct_index = idx
                        found = True
                        break
            if not found:
                correct_answer = clean_opts[0]
                correct_index = 0

        validated.append({
            "question": q_text,
            "options": clean_opts,
            "correct_answer": correct_answer,
            "correct_index": correct_index,
            "answer": correct_answer,
            "explanation": expl
        })

    return validated


def generate_fallback_mcq(text: str, num_questions: int = 5, difficulty: str = 'Medium') -> list:
    """
    Intelligent educational question generator directly derived from document content.
    Constructs valid 4-option multiple choice questions with explanations.
    """
    if not text or len(text.strip()) < 100:
        return []

    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    candidate_sentences = []
    for raw in raw_sentences:
        s = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]+', ' ', raw).strip()
        s = re.sub(r'\s+', ' ', s).strip()
        if 40 <= len(s) <= 240 and not s.startswith(('---', 'Title:', 'Presented by:', 'Author:')):
            if any(term in s.lower() for term in [
                'is', 'are', 'designed', 'system', 'process', 'using', 'requires', 'provides',
                'helps', 'analyzes', 'evaluates', 'involves', 'method', 'technology', 'model',
                'decision', 'feature', 'learning', 'component', 'data', 'platform'
            ]):
                candidate_sentences.append(s)

    seen = set()
    sentences = []
    for s in candidate_sentences:
        key = s.lower()[:50]
        if key not in seen:
            seen.add(key)
            sentences.append(s)

    if not sentences:
        paras = [p.strip() for p in text.split('\n\n') if len(p.strip()) >= 50]
        sentences = paras[:10]

    if not sentences:
        return []

    questions = []
    num_to_generate = min(num_questions, len(sentences))
    step = max(1, len(sentences) // num_to_generate)
    chosen_indices = [i * step for i in range(num_to_generate)]

    for idx, s_idx in enumerate(chosen_indices):
        if s_idx >= len(sentences):
            continue
        sentence = sentences[s_idx]

        q_text = ""
        correct_opt = ""
        wrong_opts = []

        if " is " in sentence or " are " in sentence:
            parts = re.split(r'\b(?:is|are)\b', sentence, maxsplit=1)
            subject = parts[0].strip().lstrip('-*• ')
            predicate = parts[1].strip().rstrip('.')
            if len(subject) > 8 and len(predicate) > 15:
                q_text = f"According to the document, what is the role or function of '{subject[:60]}'?"
                correct_opt = f"It is {predicate[:90]}"
                wrong_opts = [
                    "It is strictly dedicated to manual filing without digital evaluation",
                    "It was deprecated in earlier implementations",
                    "It operates without system integration or assessment"
                ]

        if not q_text:
            q_text = f"Which statement regarding '{sentence[:50]}...' is supported by the document?"
            correct_opt = sentence.rstrip('.')
            wrong_opts = [
                "The document explicitly advises against this approach",
                "This capability is scheduled for removal in future versions",
                "This requires manual intervention for every operation"
            ]

        options = [correct_opt] + wrong_opts
        random.shuffle(options)
        correct_index = options.index(correct_opt)

        questions.append({
            "question": q_text,
            "options": options,
            "correct_answer": correct_opt,
            "correct_index": correct_index,
            "answer": correct_opt,
            "explanation": f"According to the document: \"{sentence}\""
        })

        if len(questions) >= num_questions:
            break

    return questions


def generate_mcq(text, num_questions=5, difficulty='Medium'):
    """
    Generates educational multiple-choice questions from uploaded document text.
    Uses Gemini when available with fallback to document-derived questions.
    """
    if not text or len(text.strip()) < 100:
        return []

    prepared_text = prepare_content_for_quiz(text, max_chars=15000)
    client = get_gemini_client()

    if client:
        prompt = get_mcq_generation_prompt(prepared_text, num_questions=num_questions, difficulty=difficulty)
        for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash']:
            try:
                model = client.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                if response and response.text:
                    parsed = parse_and_validate_quiz_json(response.text)
                    if parsed and len(parsed) >= 1:
                        return parsed[:num_questions]
            except Exception as e:
                logger.debug(f"Quiz Generation Error ({model_name}): {e}")

    return generate_fallback_mcq(prepared_text, num_questions=num_questions, difficulty=difficulty)
