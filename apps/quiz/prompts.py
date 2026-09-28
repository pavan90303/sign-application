"""
Quiz Generation Prompts
=======================
Prompts for AI-powered educational MCQ quiz generation.
"""

def get_mcq_generation_prompt(content: str, num_questions: int = 5, difficulty: str = 'Medium') -> str:
    return f"""You are an educational quiz generator.

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
      "explanation": "Detailed explanation grounded in the text"
    }}
  ]
}}

Content:
{content}
"""
