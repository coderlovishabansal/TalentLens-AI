"""
Uses Claude to deeply re-rank the top N candidates.
Reads actual career history and reasons about fit vs the JD.
Only called on ~200 candidates, not all 100k.
"""

import json
import time
import anthropic
from pipeline.jd_parser import JD_RAW


CLIENT = None


def get_client() -> anthropic.Anthropic:
    global CLIENT
    if CLIENT is None:
        CLIENT = anthropic.Anthropic()
    return CLIENT


def format_candidate_for_llm(candidate: dict) -> str:
    p = candidate["profile"]
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    edu = candidate.get("education", [])
    signals = candidate["redrob_signals"]

    top_skills = [
        f"{s['name']} ({s['proficiency']})"
        for s in sorted(skills, key=lambda x: x.get("endorsements", 0), reverse=True)[:10]
    ]

    career_lines = []
    for j in career[:5]:
        duration = f"{j['duration_months']}mo"
        career_lines.append(
            f"  - {j['title']} at {j['company']} ({j['company_size']}, {duration}): {j['description'][:300]}"
        )

    edu_lines = [
        f"  - {e['degree']} in {e['field_of_study']}, {e['institution']} ({e.get('tier','?')})"
        for e in edu[:2]
    ]

    return f"""
CANDIDATE ID: {candidate['candidate_id']}
Headline: {p['headline']}
Current: {p['current_title']} at {p['current_company']} ({p['current_industry']})
Experience: {p['years_of_experience']} years
Location: {p['location']}, {p.get('country','')}

Top Skills: {', '.join(top_skills)}

Career History:
{chr(10).join(career_lines)}

Education:
{chr(10).join(edu_lines)}

Behavioral Signals:
  - Open to work: {signals.get('open_to_work_flag')}
  - Last active: {signals.get('last_active_date')}
  - Recruiter response rate: {signals.get('recruiter_response_rate', 0):.0%}
  - Interview completion rate: {signals.get('interview_completion_rate', 0):.0%}
  - Notice period: {signals.get('notice_period_days')} days
  - GitHub activity: {signals.get('github_activity_score')}
""".strip()


SYSTEM_PROMPT = """You are a senior technical recruiter at Redrob AI with deep expertise in ML/AI engineering.
Your task is to evaluate candidates against a specific job description and provide a precise fit score.

Be strict and accurate. Do not be fooled by:
- Candidates who have AI keywords in their skills but whose careers are unrelated (marketing, HR, etc.)
- Candidates who are behaviourally unavailable (inactive, low response rate)
- Candidates from pure consulting backgrounds with no product company experience
- Candidates who claim expertise in ML but have no production deployment history

Reward candidates who:
- Have built real production retrieval, search, or recommendation systems
- Have worked at product companies (not just services/consulting)
- Are actively looking and responsive
- Have hands-on NLP/IR experience backed by career history, not just skill tags
"""


def rerank_batch(candidates: list[dict], batch_size: int = 5) -> list[dict]:
    """
    Re-ranks candidates using Claude. Processes in batches to stay within context limits.
    Returns candidates with added 'llm_score' and 'llm_reasoning' fields.
    """
    client = get_client()
    results = []

    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        candidate_texts = "\n\n---\n\n".join(
            format_candidate_for_llm(c) for c in batch
        )

        prompt = f"""Here is the Job Description:
---
{JD_RAW}
---

Evaluate each of the following {len(batch)} candidates against this JD.

For EACH candidate, return a JSON object with:
- "candidate_id": string
- "score": integer 0-100 (100 = perfect fit, 0 = completely wrong)
- "reasoning": string, 1-2 sentences explaining the score

Return a JSON array of {len(batch)} objects. No extra text, just valid JSON.

CANDIDATES:
{candidate_texts}
"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            scored = json.loads(raw)
            id_to_score = {s["candidate_id"]: s for s in scored}

            for c in batch:
                cid = c["candidate_id"]
                if cid in id_to_score:
                    c["llm_score"] = id_to_score[cid]["score"] / 100
                    c["llm_reasoning"] = id_to_score[cid]["reasoning"]
                else:
                    c["llm_score"] = 0.5
                    c["llm_reasoning"] = "Score unavailable"
                results.append(c)

        except Exception as e:
            print(f"LLM batch {i//batch_size} failed: {e}")
            for c in batch:
                c["llm_score"] = c.get("final_score", 0.5)
                c["llm_reasoning"] = "LLM scoring unavailable; using base score."
                results.append(c)

        # Brief pause to avoid rate limits
        if i + batch_size < len(candidates):
            time.sleep(0.5)

    return results


def generate_reasoning(candidate: dict, scores: dict) -> str:
    """
    Generates a human-readable reasoning string for the CSV submission.
    Falls back to a template if LLM reasoning isn't available.
    """
    if "llm_reasoning" in candidate and candidate["llm_reasoning"]:
        return candidate["llm_reasoning"]

    # Template fallback
    p = candidate["profile"]
    matched = scores.get("matched_skills", [])
    skills_str = ", ".join(matched[:3]) if matched else "relevant skills"
    return (
        f"{p['current_title']} with {p['years_of_experience']}yrs experience; "
        f"matched on {skills_str}; "
        f"response rate {candidate['redrob_signals'].get('recruiter_response_rate', 0):.0%}."
    )
