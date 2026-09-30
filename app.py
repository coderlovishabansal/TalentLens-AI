"""
Streamlit demo app for the Redrob Intelligent Candidate Ranker.
Run with: streamlit run app.py
"""

import json
import time
from pathlib import Path

import numpy as np
import streamlit as st
import plotly.graph_objects as go

from pipeline.loader import load_candidates, load_sample
from pipeline.jd_parser import get_jd_text_for_embedding, JD_RAW
from pipeline.encoder import load_model, encode_candidates, encode_jd, cosine_similarities
from pipeline.feature_scorer import compute_structured_score
from pipeline.behavioral import score_behavioral
from pipeline.honeypot import honeypot_penalty, honeypot_flags
from pipeline.llm_reranker import rerank_batch, generate_reasoning

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Redrob AI Candidate Ranker",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Redrob Intelligent Candidate Ranker")
st.caption("AI-powered candidate discovery & ranking engine")

# ---------------------------------------------------------------------------
# Sidebar — controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    data_path = st.text_input(
        "Candidates file path",
        value="sample_candidates.json",
        help="Path to candidates.jsonl.gz or sample_candidates.json",
    )
    is_sample = st.checkbox("Sample JSON file (not .jsonl.gz)", value=True)
    top_n = st.slider("Top N candidates to show", 10, 100, 20)
    use_llm = st.checkbox("Enable Claude LLM re-ranking", value=False,
                          help="Requires ANTHROPIC_API_KEY environment variable")
    llm_n = st.slider("LLM re-ranking pool size", 10, 100, 30, disabled=not use_llm)
    run_button = st.button("🚀 Run Ranking", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# JD display
# ---------------------------------------------------------------------------
with st.expander("📄 Job Description", expanded=False):
    st.text(JD_RAW)

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
if run_button:
    with st.spinner("Loading candidates..."):
        if is_sample:
            candidates = load_sample(data_path)
        else:
            candidates = load_candidates(data_path)
    st.success(f"Loaded {len(candidates):,} candidates")

    with st.spinner("Loading embedding model..."):
        model = load_model()

    progress = st.progress(0, text="Encoding candidates...")
    jd_text = get_jd_text_for_embedding()
    jd_vec = encode_jd(jd_text, model, cache=True)
    candidate_vecs = encode_candidates(candidates, model, cache=True)
    progress.progress(33, text="Computing similarity scores...")

    # Coarse rank
    similarities = cosine_similarities(jd_vec, candidate_vecs)
    coarse_n = min(500, len(candidates))
    top_indices = np.argsort(similarities)[::-1][:coarse_n]
    coarse_candidates = [candidates[i] for i in top_indices]
    coarse_sims = [similarities[i] for i in top_indices]

    progress.progress(50, text="Fine scoring candidates...")

    # Fine score
    scored = []
    for candidate, sem_score in zip(coarse_candidates, coarse_sims):
        structured = compute_structured_score(candidate)
        behavioral = score_behavioral(candidate)
        hp = honeypot_penalty(candidate)

        base = (
            float(sem_score)              * 0.30 +
            structured["structured_score"] * 0.40 +
            behavioral["behavioral_score"] * 0.20 +
            structured["skill_score"]     * 0.05 +
            structured["career_score"]    * 0.05
        )
        final = round(base * hp, 6)

        scored.append({
            "candidate": candidate,
            "semantic_score": round(float(sem_score), 4),
            "structured": structured,
            "behavioral": behavioral,
            "honeypot_penalty": round(hp, 4),
            "final_score": final,
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    progress.progress(75, text="LLM re-ranking..." if use_llm else "Finalizing...")

    # LLM re-rank
    if use_llm:
        llm_pool = [s["candidate"] for s in scored[:llm_n]]
        for i, c in enumerate(llm_pool):
            c["final_score"] = scored[i]["final_score"]
        reranked = rerank_batch(llm_pool, batch_size=5)
        id_to_llm = {c["candidate_id"]: c for c in reranked}
        for s in scored[:llm_n]:
            cid = s["candidate"]["candidate_id"]
            if cid in id_to_llm:
                llm_s = id_to_llm[cid].get("llm_score", s["final_score"])
                s["final_score"] = round(s["final_score"] * 0.6 + llm_s * 0.4, 6)
                s["candidate"]["llm_reasoning"] = id_to_llm[cid].get("llm_reasoning", "")
        scored.sort(key=lambda x: x["final_score"], reverse=True)

    progress.progress(100, text="Done!")
    time.sleep(0.3)
    progress.empty()

    top = scored[:top_n]

    # Normalize scores
    raw_scores = [s["final_score"] for s in top]
    min_s, max_s = min(raw_scores), max(raw_scores)
    score_range = max_s - min_s if max_s > min_s else 1.0
    for s in top:
        s["display_score"] = round(0.20 + ((s["final_score"] - min_s) / score_range) * 0.79, 4)

    # -----------------------------------------------------------------------
    # Results header
    # -----------------------------------------------------------------------
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Candidates", f"{len(candidates):,}")
    col2.metric("Showing Top", top_n)
    honeypots = sum(1 for s in top if s["honeypot_penalty"] < 0.2)
    col3.metric("Honeypots in Top", honeypots, delta="OK" if honeypots <= 10 else "OVER LIMIT", delta_color="normal" if honeypots <= 10 else "inverse")
    col4.metric("Top Score", f"{top[0]['display_score']:.4f}")

    # -----------------------------------------------------------------------
    # Score distribution chart
    # -----------------------------------------------------------------------
    st.subheader("Score Distribution")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(1, top_n + 1)),
        y=[s["display_score"] for s in top],
        marker_color=[
            "#ef4444" if s["honeypot_penalty"] < 0.2 else "#3b82f6"
            for s in top
        ],
        hovertemplate="Rank %{x}<br>Score: %{y:.4f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Rank",
        yaxis_title="Score",
        height=300,
        margin=dict(t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------
    # Candidate cards
    # -----------------------------------------------------------------------
    st.subheader(f"Top {top_n} Candidates")

    for rank, s in enumerate(top, start=1):
        c = s["candidate"]
        p = c["profile"]
        beh = s["behavioral"]
        struct = s["structured"]
        hp = s["honeypot_penalty"]
        flags = honeypot_flags(c)

        is_hp = hp < 0.2
        card_color = "🔴" if is_hp else ("🟡" if hp < 0.5 else "🟢")

        reasoning = generate_reasoning(c, struct)

        with st.expander(
            f"#{rank} {card_color} **{p['current_title']}** — {p['years_of_experience']}yrs — Score: {s['display_score']:.4f}",
            expanded=(rank <= 3),
        ):
            col_a, col_b, col_c = st.columns([2, 2, 1])

            with col_a:
                st.markdown(f"**{p['anonymized_name']}**")
                st.caption(f"{p['headline']}")
                st.write(f"📍 {p['location']} | 🏢 {p['current_company']} ({p['current_industry']})")
                st.write(f"🎓 {p['current_company_size']} employees")
                if flags:
                    st.error(f"⚠️ Honeypot flags: {'; '.join(flags)}")

            with col_b:
                st.markdown("**Score Breakdown**")
                breakdown = {
                    "Semantic": s["semantic_score"],
                    "Skills": struct["skill_score"],
                    "Career": struct["career_score"],
                    "Experience": struct["exp_score"],
                    "Behavioral": beh["behavioral_score"],
                }
                for label, val in breakdown.items():
                    bar_pct = int(val * 100)
                    color = "#22c55e" if val >= 0.7 else ("#f59e0b" if val >= 0.4 else "#ef4444")
                    st.markdown(
                        f"{label}: `{val:.2f}` "
                        f'<div style="background:#e5e7eb;border-radius:4px;height:8px;margin-bottom:4px">'
                        f'<div style="width:{bar_pct}%;background:{color};height:8px;border-radius:4px"></div></div>',
                        unsafe_allow_html=True,
                    )

            with col_c:
                st.markdown("**Availability**")
                st.metric("Response Rate", f"{beh['response_rate']:.0%}")
                st.metric("Interview Rate", f"{beh['interview_completion']:.0%}")
                st.metric("Notice", f"{beh['notice_days']}d")
                st.metric("Last Active", f"{beh['inactive_days']}d ago")

            st.info(f"💡 **Why ranked here:** {reasoning}")

            if struct["matched_skills"]:
                st.success(f"✅ JD skill matches: {', '.join(struct['matched_skills'][:8])}")

    # -----------------------------------------------------------------------
    # Download button
    # -----------------------------------------------------------------------
    st.divider()
    csv_lines = ["candidate_id,rank,score,reasoning"]
    prev_score = None
    for rank, s in enumerate(top, start=1):
        cid = s["candidate"]["candidate_id"]
        score = s["display_score"]
        if prev_score is not None and score > prev_score:
            score = prev_score
        prev_score = score
        reasoning = generate_reasoning(s["candidate"], s["structured"]).replace(",", ";")
        csv_lines.append(f'{cid},{rank},{score},"{reasoning}"')

    st.download_button(
        label="⬇️ Download submission.csv",
        data="\n".join(csv_lines),
        file_name="submission.csv",
        mime="text/csv",
    )
