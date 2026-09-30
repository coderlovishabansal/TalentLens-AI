"""
Converts candidate profiles and the JD into dense vector embeddings
using a local sentence-transformer model (no API calls, no GPU needed).
"""

import numpy as np
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

CACHE_DIR = Path(__file__).parent.parent / "cache"
MODEL_NAME = "all-MiniLM-L6-v2"  # fast, 384-dim, good quality, ~80MB


def load_model() -> SentenceTransformer:
    print(f"Loading embedding model: {MODEL_NAME}")
    return SentenceTransformer(MODEL_NAME)


def build_candidate_text(candidate: dict) -> str:
    """
    Converts a candidate record into a single string for embedding.
    Weights important fields by repeating them.
    """
    p = candidate["profile"]
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    edu = candidate.get("education", [])
    certs = candidate.get("certifications", [])

    # Skills string — repeat expert/advanced skills for emphasis
    skill_parts = []
    for s in skills:
        name = s["name"]
        if s["proficiency"] in ("expert", "advanced"):
            skill_parts.extend([name, name])  # repeat for weight
        else:
            skill_parts.append(name)
    skills_text = " ".join(skill_parts)

    # Career descriptions — most important signal
    career_parts = []
    for job in career:
        career_parts.append(
            f"{job['title']} at {job['company']}: {job['description']}"
        )
    career_text = " | ".join(career_parts)

    # Education
    edu_text = " ".join(
        f"{e['degree']} in {e['field_of_study']} from {e['institution']}"
        for e in edu
    )

    # Certifications
    cert_text = " ".join(c["name"] for c in certs)

    return (
        f"{p['headline']} {p['summary']} "
        f"Current role: {p['current_title']} at {p['current_company']} "
        f"Industry: {p['current_industry']} "
        f"Skills: {skills_text} "
        f"Career: {career_text} "
        f"Education: {edu_text} "
        f"Certifications: {cert_text}"
    )


def encode_candidates(
    candidates: list[dict],
    model: SentenceTransformer,
    batch_size: int = 256,
    cache: bool = True,
) -> np.ndarray:

    # ---------------------------------------------------------
    # Use a different cache file for each dataset size
    # Example:
    # candidate_embeddings_50.npy
    # candidate_embeddings_100000.npy
    # ---------------------------------------------------------
    cache_path = CACHE_DIR / f"candidate_embeddings_{len(candidates)}.npy"

    if cache and cache_path.exists():
        cached = np.load(cache_path)
        print(f"Loading cached embeddings from {cache_path}")
        return cached

    print("Building candidate texts...")
    texts = [
        build_candidate_text(c)
        for c in tqdm(candidates, desc="Building texts")
    ]

    print(f"Encoding {len(texts):,} candidates (batch_size={batch_size})...")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    if cache:
        CACHE_DIR.mkdir(exist_ok=True)
        np.save(cache_path, embeddings)
        print(f"Cached embeddings to {cache_path}")

    return embeddings


def encode_jd(
    jd_text: str,
    model: SentenceTransformer,
    cache: bool = True,
) -> np.ndarray:

    cache_path = CACHE_DIR / "jd_embedding.npy"

    if cache and cache_path.exists():
        print("Loading cached JD embedding")
        return np.load(cache_path)

    embedding = model.encode(
        [jd_text],
        normalize_embeddings=True,
    )[0]

    if cache:
        CACHE_DIR.mkdir(exist_ok=True)
        np.save(cache_path, embedding)

    return embedding


def cosine_similarities(
    jd_vec: np.ndarray,
    candidate_vecs: np.ndarray,
) -> np.ndarray:
    """Fast dot product similarity (vectors are already normalized)."""
    return candidate_vecs @ jd_vec