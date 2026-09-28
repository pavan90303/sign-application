"""
Concept Assessment Prompts
==========================
Prompts for reference knowledge extraction, student knowledge representation,
and semantic comparison between student explanations and reference material.
"""

def get_reference_extraction_prompt(reference_text: str, topic_hint: str = "") -> str:
    return f"""
Analyze the following educational reference text and extract a structured knowledge representation JSON.
Topic hint: {topic_hint if topic_hint else 'Infer from text'}

Reference Text:
\"\"\"{reference_text}\"\"\"

Return ONLY a single valid JSON object matching this exact schema:
{{
  "topic": "Main Topic Name",
  "concepts": [
    {{
      "id": "concept_id_slug",
      "name": "Concept Name",
      "importance": "core"
    }}
  ],
  "relationships": [
    {{
      "source": "concept_id_slug_1",
      "relation": "action_or_verb",
      "target": "concept_id_slug_2"
    }}
  ]
}}

Guidelines:
1. Extract 4-10 essential core concepts (e.g. "photosynthesis", "green_plants", "sunlight", "water", "carbon_dioxide", "glucose", "oxygen").
2. Extract directed relationships between these concepts.
3. Return ONLY valid JSON.
"""


def get_student_extraction_prompt(transcript: str, topic_hint: str = "") -> str:
    return f"""
Analyze the following student explanation transcript (reconstructed from sign language) and extract the knowledge representation JSON:
Topic hint: {topic_hint if topic_hint else 'Infer from explanation'}

Student Transcript:
\"\"\"{transcript}\"\"\"

Return ONLY a single valid JSON object:
{{
  "topic": "Topic Name",
  "concepts": [
    {{
      "id": "concept_id_slug",
      "name": "Concept Name",
      "importance": "core"
    }}
  ],
  "relationships": [
    {{
      "source": "concept_id_slug_1",
      "relation": "action_or_verb",
      "target": "concept_id_slug_2"
    }}
  ]
}}
"""
