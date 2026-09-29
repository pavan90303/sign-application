"""
Document Extractor Service
==========================
Handles parsing and text extraction from PPT, PPTX, PDF, DOCX, and TXT files.
Cleans raw text to remove control characters and normalize whitespace.
"""

import os
import re
from pptx import Presentation


def clean_extracted_text(text: str) -> str:
    """
    Cleans raw extracted text:
    - Removes non-printable control characters.
    - Normalizes horizontal spaces and tabs.
    - Collapses repeated blank lines.
    - Strips leading and trailing whitespace.
    """
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
    text = text.replace('\t', ' ')
    lines = [re.sub(r' +', ' ', line).strip() for line in text.splitlines()]
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
    """Extracts educational content from PPT / PPTX files."""
    prs = Presentation(file_path)
    slides_text = []

    for slide_idx, slide in enumerate(prs.slides, start=1):
        slide_parts = [f"--- Slide {slide_idx} ---"]
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
    """Extracts text from PDF documents using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    pages_text = []
    for page_idx, page in enumerate(reader.pages, start=1):
        txt = page.extract_text()
        if txt and txt.strip():
            pages_text.append(f"--- Page {page_idx} ---\n{txt.strip()}")
    return "\n\n".join(pages_text)


def extract_docx_content(file_path: str) -> str:
    """Extracts text from Word documents using python-docx."""
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
    """Extracts text from plain text or markdown files with encoding detection."""
    for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, Exception):
            continue
    with open(file_path, 'r', errors='ignore') as f:
        return f.read()


def extract_text_from_file(file_path: str) -> str:
    """Primary dispatcher: extracts clean educational content from PPTX, PPT, PDF, DOCX, TXT."""
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
        for fn in [extract_pptx_content, extract_pdf_content, extract_docx_content, extract_plain_text]:
            try:
                raw_text = fn(file_path)
                if raw_text and len(raw_text.strip()) > 50:
                    break
            except Exception:
                continue

    return clean_extracted_text(raw_text)


def extract_ppt_text(file_path: str) -> str:
    """Backward-compatible alias for extract_text_from_file."""
    return extract_text_from_file(file_path)
