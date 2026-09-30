"""
Main entry point for the Redrob Intelligent Candidate Ranker.

Usage:
    python rank.py --candidates candidates.jsonl.gz --out submission.csv
    python rank.py --candidates candidates.jsonl.gz --out submission.csv --no-llm
    python rank.py --candidates sample_candidates.json --out submission.csv --sample
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

from pipeline.loader import load_candidates, load_sample
from pipeline.jd_parser import get_jd, get_jd_text_for_embedding
from pipeline.encoder import load_model, encode_candidates, encode_jd, cosine_similarities
from pipeline.feature_scorer import compute_structured_score
from pipeline.behavioral import score_behavioral
from pipeline.honeypot import honeypot_penalty, is_honeypot
from pipeline.llm_reranker import rerank_batch, generate_reasoning


def parse_args():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl.gz or sample_candidates.json")
    parser.add_argument("--out", default="submission.csv", help="Output CSV path")
    parser.add_argument("--top-n", type=int, default=100, help="Number of candidates to output")
    parser.add_argument("--coarse-n", type=int, default=500, help="Candidates to pass from coarse to fine ranking")
    parser.add_argument("--llm-n", type=int, default=200, help="Candidates to pass to LLM re-ranker")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM re-ranking (faster, no API key needed)")
    parser.add_argument("--no-cache", action="store_true", help="Recompute embeddings even if cache exists")
    parser.add_argument("--sample", action="store_true", help="Load from JSON array (sample_candidates.json)")
    return parser.parse_args()


def compute_final_score(
    semantic_score: float,
    structured: dict,
    behavioral: dict,
    hp_penalty: float,
) -> float:
    """
    Combines all scoring components into a single final score.

    Weights:
      - Semantic similarity (embedding): 30%
      - Structured features (skills, career, exp, edu, location): 40%
      - Behavioral signals (availability, responsiveness): 20%
      - Honeypot penalty: multiplier
    """
    base = (
        semantic_score             * 0.30 +
        structured["structured_score"] * 0.40 +
        behavioral["behavioral_score"] * 0.20 +
        structured["skill_score"]  * 0.05 +   # extra weight on skills
        structured["career_score"] * 0.05      # extra weight on career
    )
    return round(base * hp_penalty, 6)


def main():
    args = parse_args()
    start_time = time.time()

    # -----------------------------------------------------------------------
    # 1. Load candidates
    # -----------------------------------------------------------------------
    print("\n[1/6] Loading candidates...")
    if args.sample:
        candidates = load_sample(args.candidates)
    else:
        candidates = load_candidates(args.candidates)
    print(f"  Loaded {len(candidates):,} candidates")

    # -----------------------------------------------------------------------
    # 2. Encode JD + candidates
    # -----------------------------------------------------------------------
    print("\n[2/6] Encoding (embedding model)...")
    model = load_model()
    use_cache = not args.no_cache

    jd_text = get_jd_text_for_embedding()
    jd_vec = encode_jd(jd_text, model, cache=use_cache)
    candidate_vecs = encode_candidates(candidates, model, cache=use_cache)

    # -----------------------------------------------------------------------
    # 3. Coarse ranking — semantic similarity
    # -----------------------------------------------------------------------
    print(f"\n[3/6] Coarse ranking (semantic similarity → top {args.coarse_n})...")
    similarities = cosine_similarities(jd_vec, candidate_vecs)
    top_indices = np.argsort(similarities)[::-1][:args.coarse_n]
    coarse_candidates = [candidates[i] for i in top_indices]
    coarse_similarities = [similarities[i] for i in top_indices]
    print(f"  Top similarity: {coarse_similarities[0]:.4f}, bottom: {coarse_similarities[-1]:.4f}")

    # -----------------------------------------------------------------------
    # 4. Fine ranking — structured features + behavioral + honeypot
    # -----------------------------------------------------------------------
    print(f"\n[4/6] Fine scoring {len(coarse_candidates)} candidates...")
    scored = []

    for i, (candidate, sem_score) in enumerate(
        tqdm(zip(coarse_candidates, coarse_similarities), total=len(coarse_candidates), desc="Scoring")
    ):
        structured = compute_structured_score(candidate)
        behavioral = score_behavioral(candidate)
        hp = honeypot_penalty(candidate)

        final = compute_final_score(sem_score, structured, behavioral, hp)

        scored.append({
            "candidate": candidate,
            "semantic_score": round(float(sem_score), 4),
            "structured": structured,
            "behavioral": behavioral,
            "honeypot_penalty": round(hp, 4),
            "final_score": round(final, 6),
        })

    # Sort by final score
    scored.sort(key=lambda x: x["final_score"], reverse=True)
    print(f"  Top final score: {scored[0]['final_score']:.4f}")

    # -----------------------------------------------------------------------
    # 5. LLM re-ranking (optional)
    # -----------------------------------------------------------------------
    if not args.no_llm:
        llm_pool_size = min(args.llm_n, len(scored))
        print(f"\n[5/6] LLM re-ranking top {llm_pool_size} candidates with Claude...")

        llm_pool = [s["candidate"] for s in scored[:llm_pool_size]]
        # Attach pre-computed scores for fallback
        for i, c in enumerate(llm_pool):
            c["final_score"] = scored[i]["final_score"]
            c["_score_data"] = scored[i]

        reranked = rerank_batch(llm_pool, batch_size=5)

        # Blend LLM score with final score
        id_to_llm = {c["candidate_id"]: c for c in reranked}
        for s in scored[:llm_pool_size]:
            cid = s["candidate"]["candidate_id"]
            if cid in id_to_llm and "llm_score" in id_to_llm[cid]:
                llm_s = id_to_llm[cid]["llm_score"]
                s["llm_score"] = llm_s
                s["llm_reasoning"] = id_to_llm[cid].get("llm_reasoning", "")
                # Blend: 60% base + 40% LLM
                s["final_score"] = round(s["final_score"] * 0.60 + llm_s * 0.40, 6)
                s["candidate"]["llm_reasoning"] = s["llm_reasoning"]

        # Re-sort after LLM blending
        scored.sort(key=lambda x: x["final_score"], reverse=True)
        print(f"  LLM re-ranking complete. New top score: {scored[0]['final_score']:.4f}")
    else:
        print("\n[5/6] Skipping LLM re-ranking (--no-llm)")

    # -----------------------------------------------------------------------
    # 6. Write submission CSV
    # -----------------------------------------------------------------------
    print(f"\n[6/6] Writing top {args.top_n} to {args.out}...")
    top = scored[:args.top_n]

    # Normalise scores to [0.2, 0.99] range so they're non-increasing and bounded
    raw_scores = [s["final_score"] for s in top]
    min_s, max_s = min(raw_scores), max(raw_scores)
    score_range = max_s - min_s if max_s > min_s else 1.0

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        prev_norm = None
        for rank, s in enumerate(top, start=1):
            cid = s["candidate"]["candidate_id"]

            # Normalize to 0.20–0.99
            norm = 0.20 + ((s["final_score"] - min_s) / score_range) * 0.79
            norm = round(norm, 4)

            # Ensure strictly non-increasing (tie = same score, already handled by sort)
            if prev_norm is not None and norm > prev_norm:
                norm = prev_norm
            prev_norm = norm

            reasoning = generate_reasoning(s["candidate"], s["structured"])
            writer.writerow([cid, rank, norm, reasoning])

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.1f}s. Output: {args.out}")
    print(f"Top candidate: {scored[0]['candidate']['profile']['current_title']} "
          f"({scored[0]['candidate']['profile']['years_of_experience']}yrs)")

    # Honeypot check
    honeypots_in_top = sum(
        1 for s in top if s["honeypot_penalty"] < 0.2
    )
    print(f"Honeypot candidates in top {args.top_n}: {honeypots_in_top} "
          f"({'OK' if honeypots_in_top <= 10 else 'WARNING: exceeds limit!'})")


if __name__ == "__main__":
    main()
