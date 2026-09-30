"""
FastAPI backend for the Redrob Intelligent Candidate Ranker.

Wraps the existing scoring pipeline (pipeline/) behind a REST API so the
React frontend can drive it instead of Streamlit. Scoring logic mirrors
app.py / rank.py exactly.

Run with: uvicorn server:app --reload --port 8000
"""

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.loader import load_candidates, load_sample
from pipeline.jd_parser import get_jd, get_jd_text_for_embedding
from pipeline.encoder import load_model, encode_candidates, encode_jd, cosine_similarities
from pipeline.feature_scorer import compute_structured_score
from pipeline.behavioral import score_behavioral
from pipeline.honeypot import honeypot_penalty, honeypot_flags
from pipeline.llm_reranker import rerank_batch, generate_reasoning

app = FastAPI(title="Redrob Candidate Ranker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None
_candidates_cache: dict[str, list[dict]] = {}


def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


def get_candidates(data_path: str, is_sample: bool) -> list[dict]:
    key = f"{data_path}|{is_sample}"
    if key not in _candidates_cache:
        try:
            _candidates_cache[key] = (
                load_sample(data_path) if is_sample else load_candidates(data_path)
            )
        except FileNotFoundError:
            raise HTTPException(404, f"Candidates file not found: {data_path}")
    return _candidates_cache[key]


class RankRequest(BaseModel):
    data_path: str = "sample_candidates.json"
    is_sample: bool = True
    top_n: int = 20
    use_llm: bool = False
    llm_n: int = 30
    coarse_n: int = 500


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/jd")
def api_jd():
    return get_jd()


@app.post("/api/rank")
def api_rank(req: RankRequest):
    candidates = get_candidates(req.data_path, req.is_sample)

    model = get_model()
    jd_text = get_jd_text_for_embedding()
    jd_vec = encode_jd(jd_text, model, cache=True)
    candidate_vecs = encode_candidates(candidates, model, cache=True)

    similarities = cosine_similarities(jd_vec, candidate_vecs)
    coarse_n = min(req.coarse_n, len(candidates))
    top_indices = np.argsort(similarities)[::-1][:coarse_n]
    coarse_candidates = [candidates[i] for i in top_indices]
    coarse_sims = [similarities[i] for i in top_indices]

    scored = []
    for candidate, sem_score in zip(coarse_candidates, coarse_sims):
        structured = compute_structured_score(candidate)
        behavioral = score_behavioral(candidate)
        hp = honeypot_penalty(candidate)
        base = (
            float(sem_score) * 0.30
            + structured["structured_score"] * 0.40
            + behavioral["behavioral_score"] * 0.20
            + structured["skill_score"] * 0.05
            + structured["career_score"] * 0.05
        )
        scored.append({
            "candidate": candidate,
            "semantic_score": round(float(sem_score), 4),
            "structured": structured,
            "behavioral": behavioral,
            "honeypot_penalty": round(hp, 4),
            "final_score": round(base * hp, 6),
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)

    if req.use_llm:
        llm_n = min(req.llm_n, len(scored))
        llm_pool = [s["candidate"] for s in scored[:llm_n]]
        for i, c in enumerate(llm_pool):
            c["final_score"] = scored[i]["final_score"]
        try:
            reranked = rerank_batch(llm_pool, batch_size=5)
        except Exception as e:
            raise HTTPException(500, f"LLM re-ranking failed: {e}")

        id_to_llm = {c["candidate_id"]: c for c in reranked}
        for s in scored[:llm_n]:
            cid = s["candidate"]["candidate_id"]
            if cid in id_to_llm:
                llm_s = id_to_llm[cid].get("llm_score", s["final_score"])
                s["final_score"] = round(s["final_score"] * 0.6 + llm_s * 0.4, 6)
                s["candidate"]["llm_reasoning"] = id_to_llm[cid].get("llm_reasoning", "")
        scored.sort(key=lambda x: x["final_score"], reverse=True)

    top_n = min(req.top_n, len(scored))
    top = scored[:top_n]
    raw_scores = [s["final_score"] for s in top]
    min_s, max_s = min(raw_scores), max(raw_scores)
    score_range = max_s - min_s if max_s > min_s else 1.0

    results = []
    prev_display = None
    for rank, s in enumerate(top, start=1):
        c = s["candidate"]
        p = c["profile"]
        display_score = round(0.20 + ((s["final_score"] - min_s) / score_range) * 0.79, 4)
        if prev_display is not None and display_score > prev_display:
            display_score = prev_display
        prev_display = display_score

        results.append({
            "candidate_id": c["candidate_id"],
            "rank": rank,
            "display_score": display_score,
            "name": p["anonymized_name"],
            "headline": p["headline"],
            "current_title": p["current_title"],
            "years_of_experience": p["years_of_experience"],
            "location": p["location"],
            "current_company": p["current_company"],
            "current_industry": p["current_industry"],
            "current_company_size": p["current_company_size"],
            "semantic_score": s["semantic_score"],
            "structured": s["structured"],
            "behavioral": s["behavioral"],
            "honeypot_penalty": s["honeypot_penalty"],
            "honeypot_flags": honeypot_flags(c),
            "reasoning": generate_reasoning(c, s["structured"]),
        })

    honeypots_in_top = sum(1 for r in results if r["honeypot_penalty"] < 0.2)

    return {
        "total_candidates": len(candidates),
        "top_n": top_n,
        "honeypots_in_top": honeypots_in_top,
        "top_score": results[0]["display_score"] if results else 0,
        "results": results,
    }
