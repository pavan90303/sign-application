import os
import re
import json
import random
import string
from pptx import Presentation
import google.genai as genai
from google.genai import types
from django.conf import settings


def clean_extracted_text(text: str) -> str:
    """
    Cleans raw extracted text:
    - Removes unreadable/non-printable control characters.
    - Normalizes excessive horizontal whitespace and tabs.
    - Collapses repeated blank lines into at most one blank line.
    - Strips leading and trailing whitespace.
    """
    if not text:
        return ""
    # Strip null bytes and non-printable control characters (keeping \t, \n, \r)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
    # Normalize tabs to spaces
    text = text.replace('\t', ' ')
    # Normalize multiple horizontal spaces per line
    lines = [re.sub(r' +', ' ', line).strip() for line in text.splitlines()]
    # Remove repeated blank lines
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned_lines.append("")
                prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False
    return "\n".join(cleaned_lines).strip()


def extract_pptx_content(file_path: str) -> str:
    """
    Extracts educational content from PPT / PPTX files using python-pptx:
    - Slide titles
    - Text boxes and shapes
    - Bullet points (indented with '-')
    - Tables (rows and cells)
    """
    prs = Presentation(file_path)
    slides_text = []

    for slide_idx, slide in enumerate(prs.slides, start=1):
        slide_parts = [f"--- Slide {slide_idx} ---"]
        title_text = ""
        if slide.shapes.title and slide.shapes.title.text:
            title_text = slide.shapes.title.text.strip()
            if title_text:
                slide_parts.append(f"Title: {title_text}")

        for shape in slide.shapes:
            if shape == slide.shapes.title:
                continue
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    p_text = paragraph.text.strip()
                    if p_text:
                        if paragraph.level > 0:
                            slide_parts.append(f"- {p_text}")
                        else:
                            slide_parts.append(p_text)
            elif shape.has_table:
                for row in shape.table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        slide_parts.append(" | ".join(row_texts))

        if len(slide_parts) > 1:
            slides_text.append("\n".join(slide_parts))

    return "\n\n".join(slides_text)


def extract_pdf_content(file_path: str) -> str:
    """
    Extracts text from PDF documents using pypdf.
    """
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    pages_text = []
    for page_idx, page in enumerate(reader.pages, start=1):
        txt = page.extract_text()
        if txt and txt.strip():
            pages_text.append(f"--- Page {page_idx} ---\n{txt.strip()}")
    return "\n\n".join(pages_text)


def extract_docx_content(file_path: str) -> str:
    """
    Extracts text from Word documents using python-docx.
    """
    import docx
    doc = docx.Document(file_path)
    paras = []
    for p in doc.paragraphs:
        if p.text.strip():
            paras.append(p.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                paras.append(" | ".join(row_texts))
    return "\n\n".join(paras)


def extract_plain_text(file_path: str) -> str:
    """
    Extracts text from plain text or markdown files with encoding detection.
    """
    for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, Exception):
            continue
    with open(file_path, 'r', errors='ignore') as f:
        return f.read()


def extract_text_from_file(file_path: str) -> str:
    """
    Primary dispatcher: extracts clean educational content from PPTX, PPT, PDF, DOCX, TXT.
    """
    if not file_path or not os.path.exists(file_path):
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    raw_text = ""

    if ext in ['.pptx', '.ppt']:
        try:
            raw_text = extract_pptx_content(file_path)
        except Exception as e:
            print(f"PPTX extraction error: {e}")
    elif ext == '.pdf':
        try:
            raw_text = extract_pdf_content(file_path)
        except Exception as e:
            print(f"PDF extraction error: {e}")
    elif ext in ['.docx', '.doc']:
        try:
            raw_text = extract_docx_content(file_path)
        except Exception as e:
            print(f"DOCX extraction error: {e}")
    elif ext in ['.txt', '.text', '.md']:
        raw_text = extract_plain_text(file_path)
    else:
        # Fallback detection across available extractors
        for fn in [extract_pptx_content, extract_pdf_content, extract_docx_content, extract_plain_text]:
            try:
                raw_text = fn(file_path)
                if raw_text and len(raw_text.strip()) > 50:
                    break
            except Exception:
                continue

    return clean_extracted_text(raw_text)


def extract_ppt_text(file_path: str) -> str:
    """
    Backward-compatible alias for existing views.
    """
    return extract_text_from_file(file_path)


def prepare_content_for_quiz(text: str, max_chars: int = 15000) -> str:
    """
    Handles large files:
    - If text <= max_chars, returns text as-is.
    - If text > max_chars, splits into sections (slides/pages/paragraphs).
    - Distributes quota evenly across beginning, middle, and end of the document.
    - Prioritizes titles, headings, bullet points, definitions, and explanations.
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
        else:
            remaining = max_chars - current_length - 2
            if remaining > 100:
                selected_parts.append(sec_text[:remaining])
            break

    return "\n\n".join(selected_parts)


def get_gemini_client():
    """
    Returns a configured Gemini API client, or None if key is missing/placeholder.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY', None)
    if not api_key or api_key in ['PLACEHOLDER_KEY', 'your_gemini_api_key_here', '']:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        return None


def summarize_text(text):
    """
    Summarizes the given text using Google Gemini (or structured document analysis fallback).
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
        schema = {
            "type": "OBJECT",
            "properties": {
                "summary": {"type": "STRING"},
                "key_concepts": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING"},
                            "description": {"type": "STRING"},
                            "color": {"type": "STRING", "enum": ["green", "blue", "purple"]}
                        },
                        "required": ["title", "description", "color"]
                    }
                },
                "important_terms": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                }
            },
            "required": ["summary", "key_concepts", "important_terms"]
        }

        prompt = f"""Analyze the following presentation content and provide a structured learning summary.

1. **summary**: A concise executive summary paragraph (approx 3-5 sentences) suitable for a quick overview.
2. **key_concepts**: Extract 3-5 key concepts. For each, provide a short 'title', a 'description', and assign a 'color' (green, blue, or purple) based on category/importance.
3. **important_terms**: List specific nouns/verbs that are crucial for sign language practice.

Content:
{text[:10000]}
"""
        for model_name in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        response_schema=schema
                    )
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"Summary Generation Error ({model_name}): {e}")

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


def parse_and_validate_quiz_json(raw_text: str) -> list:
    """
    Parses and strictly validates Gemini response into required schema:
    - Strips markdown code blocks (```json ... ```)
    - Locates JSON array or object
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
        print(f"JSON parsing error: {e}. Raw text snippet: {cleaned[:200]}")
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
    Extracts key sentences, statements, and definitions, constructing valid 4-option
    multiple choice questions with exact answers and explanations.
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
    Generates educational multiple-choice questions from the uploaded document text.
    Uses Google Gemini when configured, with safe JSON parsing and schema validation.
    Falls back gracefully to document-derived questions if Gemini is unavailable,
    ensuring the user experience is always functional.
    """
    if not text or len(text.strip()) < 100:
        return []

    prepared_text = prepare_content_for_quiz(text, max_chars=15000)
    client = get_gemini_client()

    if client:
        prompt = f"""You are an educational quiz generator.

Create {num_questions} multiple-choice questions using ONLY the educational content provided below.

Do not use outside information.
Difficulty Level: {difficulty}.

Each question must contain:
- question
- exactly 4 options
- correct_answer
- explanation

Return ONLY valid JSON.

Required JSON format:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": "Option A",
      "explanation": "Short explanation"
    }}
  ]
}}

DOCUMENT CONTENT:

{prepared_text}
"""

        for model_name in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                    )
                )
                if response and response.text:
                    parsed = parse_and_validate_quiz_json(response.text)
                    if parsed and len(parsed) > 0:
                        return parsed[:num_questions]
            except Exception as e:
                err_str = str(e)
                print(f"Gemini generation error with {model_name}: {err_str}")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "API_KEY_INVALID" in err_str:
                    break

    # If Gemini is not configured or failed, generate from document content
    print("Generating educational quiz questions from document text content...")
    return generate_fallback_mcq(text, num_questions, difficulty)

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from django.contrib.staticfiles import finders
import string

def process_text_for_sign_language(text):
    """
    Processes text to return a list of words suitable for sign language animation.
    Filters stop words, lemmatizes, and checks for file existence.
    """
    if not text:
        return []

    text = text.lower()
    try:
        words = word_tokenize(text)
    except LookupError:
        nltk.download('punkt')
        words = word_tokenize(text)

    try:
        tagged = nltk.pos_tag(words)
    except LookupError:
        nltk.download('averaged_perceptron_tagger')
        tagged = nltk.pos_tag(words)

    # Simplified tense logic (defaulting to present for summary)
    
    stop_words = set(["mightn't", 're', 'wasn', 'wouldn', 'be', 'has', 'that', 'does', 'shouldn', 'do', "you've",'off', 'for', "didn't", 'm', 'ain', 'haven', "weren't", 'are', "she's", "wasn't", 'its', "haven't", "wouldn't", 'don', 'weren', 's', "you'd", "don't", 'doesn', "hadn't", 'is', 'was', "that'll", "should've", 'a', 'then', 'the', 'mustn', 'i', 'nor', 'as', "it's", "needn't", 'd', 'am', 'have',  'hasn', 'o', "aren't", "you'll", "couldn't", "you're", "mustn't", 'didn', "doesn't", 'll', 'an', 'hadn', 'whom', 'y', "hasn't", 'itself', 'couldn', 'needn', "shan't", 'isn', 'been', 'such', 'shan', "shouldn't", 'aren', 'being', 'were', 'did', 'ma', 't', 'having', 'mightn', 've', "isn't", "won't"])

    lr = WordNetLemmatizer()
    try:
        lr.lemmatize('test')
    except LookupError:
        nltk.download('wordnet')
        nltk.download('omw-1.4')

    filtered_text = []
    for w, p in zip(words, tagged):
        if w not in stop_words and w not in string.punctuation:
            if p[1] in ['VBG', 'VBD', 'VBZ', 'VBN', 'NN']:
                filtered_text.append(lr.lemmatize(w, pos='v'))
            elif p[1] in ['JJ', 'JJR', 'JJS', 'RBR', 'RBS']:
                filtered_text.append(lr.lemmatize(w, pos='a'))
            else:
                filtered_text.append(lr.lemmatize(w))

    # Match with existing assets
    final_words = []
    for w in filtered_text:
        # Capitalize first letter as assets are mostly TitleCase or uppercase
        w_title = w.capitalize() 
        path = w_title + ".mp4"
        
        # Check specific naming conventions if needed (e.g. "Do Not")
        # For now, simplistic check
        
        if finders.find(path):
            final_words.append(w_title)
        else:
            # If word not found, spell it out (return individual chars)
            # Or just append the word and let frontend handle spelling if missing?
            # The existing logic split it. Let's split it here to be safe and consistent.
            for c in w:
                if c.isalnum():
                    final_words.append(c.upper())

    return final_words
