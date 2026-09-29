"""
Concept Comparator Service
==========================
Performs semantic vector comparison (SentenceTransformers) and topological
graph comparison (NetworkX) between reference concept knowledge and student explanation.
"""

import logging
import numpy as np
from .graph_generator import build_networkx_knowledge_graph

logger = logging.getLogger(__name__)

_EMBED_MODEL = None


def get_sentence_transformer():
    """Lazy singleton loader for SentenceTransformer embedding model."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"[AI MODEL] SentenceTransformer fallback: {e}")
            _EMBED_MODEL = False
    return _EMBED_MODEL if _EMBED_MODEL is not False else None


def perform_semantic_concept_comparison(reference_json: dict, student_json: dict, reconstructed_text: str) -> dict:
    """
    Multi-stage semantic & graph comparison:
    Uses SentenceTransformers vector embeddings and NetworkX topological alignment.
    Categorizes concepts into understood, partially understood, missing, and misconception.
    """
    raw_ref = reference_json.get("concepts", [])
    ref_concepts = []
    for item in raw_ref:
        if isinstance(item, dict):
            ref_concepts.append(str(item.get("name") or item.get("id") or ""))
        else:
            ref_concepts.append(str(item))
    ref_concepts = [c.lower().strip() for c in ref_concepts if c.strip()]
    ref_rels = reference_json.get("relationships", [])

    raw_stu = student_json.get("concepts", [])
    stu_concepts = []
    for item in raw_stu:
        if isinstance(item, dict):
            stu_concepts.append(str(item.get("name") or item.get("id") or ""))
        else:
            stu_concepts.append(str(item))
    stu_concepts = [c.lower().strip() for c in stu_concepts if c.strip()]
    stu_rels = student_json.get("relationships", [])

    reconstructed_lower = (reconstructed_text or "").lower()

    G_ref = build_networkx_knowledge_graph(raw_ref, ref_rels)
    G_stu = build_networkx_knowledge_graph(raw_stu, stu_rels)

    embed_model = get_sentence_transformer()
    sim_matrix = None
    if embed_model and ref_concepts and stu_concepts:
        try:
            from sentence_transformers import util
            ref_emb = embed_model.encode(ref_concepts, convert_to_tensor=True)
            stu_emb = embed_model.encode(stu_concepts, convert_to_tensor=True)
            sim_matrix = util.cos_sim(ref_emb, stu_emb).cpu().numpy()
        except Exception as e:
            logger.warning(f"[EMBEDDING] Vector cosine similarity fallback: {e}")

    concept_results = []
    matched_count = 0
    partial_count = 0
    missing_count = 0
    misconception_count = 0

    synonyms = {
        "glucose": ["sugar", "carbohydrate", "food", "energy"],
        "plants": ["plant", "flora", "green plants", "leaves"],
        "sunlight": ["sun", "solar energy", "light"],
        "water": ["h2o", "moisture"],
        "carbon dioxide": ["co2", "carbon-dioxide", "carbon gas"],
        "oxygen": ["o2", "air", "fresh air"]
    }

    for idx, ref_c in enumerate(ref_concepts):
        direct_match = ref_c in stu_concepts or ref_c in reconstructed_lower
        syn_match = False
        syn_word = ""
        embedding_match = False
        best_sim = 0.0

        if sim_matrix is not None and idx < sim_matrix.shape[0]:
            row_sims = sim_matrix[idx]
            max_sim_idx = int(np.argmax(row_sims))
            best_sim = float(row_sims[max_sim_idx])
            if best_sim >= 0.72:
                embedding_match = True
                syn_word = stu_concepts[max_sim_idx]
            elif best_sim >= 0.48:
                syn_match = True
                syn_word = stu_concepts[max_sim_idx]

        if not direct_match and not embedding_match:
            for syn in synonyms.get(ref_c, []):
                if syn in stu_concepts or syn in reconstructed_lower:
                    syn_match = True
                    syn_word = syn
                    break

        if direct_match or embedding_match:
            status = "understood"
            matched_count += 1
            feedback = f"✓ '{ref_c.capitalize()}' was correctly identified and communicated."
        elif syn_match:
            status = "partially_understood"
            partial_count += 1
            feedback = f"△ '{ref_c.capitalize()}' was represented as '{syn_word}', capturing essential aspects."
        else:
            status = "missing"
            missing_count += 1
            feedback = f"✕ '{ref_c.capitalize()}' was not represented in the sign explanation."

        concept_results.append({
            "concept_name": ref_c.capitalize(),
            "status": status,
            "confidence": round(max(0.70, best_sim), 2) if (direct_match or embedding_match) else (0.85 if syn_match else 0.90),
            "feedback": feedback
        })

    if "oxygen" in reconstructed_lower and "carbon dioxide" in reconstructed_lower:
        if "from carbon dioxide" in reconstructed_lower or "produces carbon dioxide" in reconstructed_lower:
            misconception_count += 1
            concept_results.append({
                "concept_name": "Carbon Dioxide & Oxygen Relationship",
                "status": "misconception",
                "confidence": 0.90,
                "feedback": "⚠ Contradiction detected: green plants absorb carbon dioxide and release oxygen during photosynthesis."
            })

    matched_rels_count = 0
    total_ref_rels = max(1, len(ref_rels))
    for r_ref in ref_rels:
        s_ref = str(r_ref.get("source", "")).lower()
        t_ref = str(r_ref.get("target", "")).lower()

        rel_matched = False
        if G_stu.has_edge(s_ref, t_ref):
            rel_matched = True
        else:
            for r_stu in stu_rels:
                s_stu = str(r_stu.get("source", "")).lower()
                t_stu = str(r_stu.get("target", "")).lower()
                if (s_ref in s_stu or s_stu in s_ref) and (t_ref in t_stu or t_stu in t_ref):
                    rel_matched = True
                    break
            if not rel_matched and (s_ref in reconstructed_lower and t_ref in reconstructed_lower):
                rel_matched = True

        if rel_matched:
            matched_rels_count += 1

    total_ref_concepts = max(1, len(ref_concepts))
    concept_coverage = round(min(1.0, (matched_count + 0.5 * partial_count) / total_ref_concepts), 3)
    relationship_accuracy = round(min(1.0, matched_rels_count / total_ref_rels), 3)
    explanation_completeness = round(min(1.0, len(stu_concepts) / total_ref_concepts), 3)

    overall_score = round(0.50 * concept_coverage + 0.40 * relationship_accuracy + 0.10 * explanation_completeness, 3)

    tot = max(1, len(concept_results))
    cat_summary = {
        "understood_count": matched_count,
        "partially_understood_count": partial_count,
        "missing_count": missing_count,
        "misconception_count": misconception_count,
        "understood_pct": int(round((matched_count / tot) * 100)),
        "partially_understood_pct": int(round((partial_count / tot) * 100)),
        "missing_pct": int(round((missing_count / tot) * 100)),
        "misconception_pct": int(round((misconception_count / tot) * 100))
    }

    return {
        "concept_results": concept_results,
        "concept_coverage": concept_coverage,
        "relationship_accuracy": relationship_accuracy,
        "overall_score": overall_score,
        "category_summary": cat_summary,
        "matched_concepts": matched_count,
        "partial_concepts": partial_count,
        "missing_concepts": missing_count,
        "misconceptions": misconception_count,
        "networkx_graph_nodes": len(G_ref.nodes),
        "networkx_graph_edges": len(G_ref.edges),
        "student_knowledge_graph": student_json
    }
