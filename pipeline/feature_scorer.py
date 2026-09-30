"""
Extracts structured features from each candidate and scores them
against the JD requirements. Pure rule-based, no ML model needed.
"""

from datetime import date, datetime
from pipeline.jd_parser import get_jd

JD = get_jd()


# ---------------------------------------------------------------------------
# Skill scoring
# ---------------------------------------------------------------------------

def score_skills(candidate: dict) -> tuple[float, int, list[str]]:
    """
    Returns (score 0-1, must_have_matches count, matched_skill_names).
    Rewards must-have skills more heavily than nice-to-haves.
    Also checks assessment scores to avoid rewarding self-reported lies.
    """
    skills = candidate.get("skills", [])
    assessment_scores = candidate["redrob_signals"].get("skill_assessment_scores", {})

    skill_names_lower = {s["name"].lower() for s in skills}
    skill_proficiency = {s["name"].lower(): s["proficiency"] for s in skills}
    skill_endorsements = {s["name"].lower(): s["endorsements"] for s in skills}
    skill_duration = {s["name"].lower(): s.get("duration_months", 0) for s in skills}

    must_have = JD["must_have_skills"]
    nice_to_have = JD["nice_to_have_skills"]

    matched_must = []
    matched_nice = []

    for skill in must_have:
        if any(skill in name for name in skill_names_lower):
            matched_must.append(skill)

    for skill in nice_to_have:
        if any(skill in name for name in skill_names_lower):
            matched_nice.append(skill)

    must_score = len(matched_must) / len(must_have)
    nice_score = len(matched_nice) / len(nice_to_have)

    # Penalty: if skill is claimed as "expert" but assessment score is poor
    assessment_penalty = 1.0
    for name, score in assessment_scores.items():
        name_lower = name.lower()
        if skill_proficiency.get(name_lower) in ("expert", "advanced") and score < 40:
            assessment_penalty *= 0.85

    final_score = (must_score * 0.75 + nice_score * 0.25) * assessment_penalty
    return final_score, len(matched_must), matched_must


# ---------------------------------------------------------------------------
# Career / title scoring
# ---------------------------------------------------------------------------

def score_career(candidate: dict) -> float:
    """
    Scores career trajectory. Checks:
    - Current/past titles match AI/ML/search domain
    - Career descriptions mention relevant work
    - Not from consulting-only background
    - Worked at product companies
    """
    profile = candidate["profile"]
    career = candidate.get("career_history", [])

    current_title_lower = profile["current_title"].lower()

    # Title match
    strong_title = any(
        t in current_title_lower for t in JD["strong_title_signals"]
    )
    weak_title = any(
        t in current_title_lower for t in JD["weak_title_signals"]
    )

    title_score = 1.0 if strong_title else (0.2 if weak_title else 0.5)

    # Career description keyword match
    career_text = " ".join(
        j["description"].lower() for j in career
    )
    career_keywords = [
        "retrieval", "ranking", "search", "recommendation", "embedding",
        "nlp", "machine learning", "deep learning", "vector", "semantic",
        "production", "deployed", "scale", "inference", "model",
        "evaluation", "a/b", "ndcg", "mrr",
    ]
    keyword_hits = sum(1 for kw in career_keywords if kw in career_text)
    career_keyword_score = min(keyword_hits / 10, 1.0)

    # Consulting penalty
    all_companies = [j["company"].lower() for j in career]
    all_companies.append(profile["current_company"].lower())
    consulting_count = sum(
        1 for company in all_companies
        if any(c in company for c in JD["consulting_companies"])
    )
    total_jobs = len(career) + 1
    consulting_ratio = consulting_count / max(total_jobs, 1)

    if consulting_ratio >= 1.0:
        consulting_penalty = 0.2  # entire career at consulting = very bad
    elif consulting_ratio > 0.5:
        consulting_penalty = 0.6
    else:
        consulting_penalty = 1.0

    # Product company bonus
    company_sizes = [j["company_size"] for j in career]
    has_mid_to_large = any(
        size in ("201-500", "501-1000", "1001-5000", "5001-10000", "10001+")
        for size in company_sizes
    )
    company_bonus = 1.1 if has_mid_to_large else 1.0

    score = (
        title_score * 0.4 +
        career_keyword_score * 0.6
    ) * consulting_penalty * company_bonus

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Experience scoring
# ---------------------------------------------------------------------------

def score_experience(candidate: dict) -> float:
    yoe = candidate["profile"]["years_of_experience"]
    ideal_min = JD["experience_ideal_min"]
    ideal_max = JD["experience_ideal_max"]
    min_ok = JD["experience_min"]
    max_ok = JD["experience_max"]

    if ideal_min <= yoe <= ideal_max:
        return 1.0
    elif min_ok <= yoe < ideal_min:
        return 0.75
    elif ideal_max < yoe <= max_ok:
        return 0.85
    elif 3 <= yoe < min_ok:
        return 0.5
    elif yoe > max_ok:
        return 0.7  # over-experienced, not disqualifying
    else:
        return 0.2


# ---------------------------------------------------------------------------
# Education scoring
# ---------------------------------------------------------------------------

def score_education(candidate: dict) -> float:
    edu = candidate.get("education", [])
    if not edu:
        return 0.5

    tier_scores = {
        "tier_1": 1.0,
        "tier_2": 0.8,
        "tier_3": 0.6,
        "tier_4": 0.4,
        "unknown": 0.5,
    }

    best_tier_score = max(
        tier_scores.get(e.get("tier", "unknown"), 0.5) for e in edu
    )

    # Bonus for relevant field
    relevant_fields = [
        "computer science", "information technology", "engineering",
        "mathematics", "statistics", "data science", "artificial intelligence",
    ]
    fields = [e["field_of_study"].lower() for e in edu]
    field_bonus = 1.1 if any(
        rf in f for rf in relevant_fields for f in fields
    ) else 1.0

    return min(best_tier_score * field_bonus, 1.0)


# ---------------------------------------------------------------------------
# Location scoring
# ---------------------------------------------------------------------------

def score_location(candidate: dict) -> float:
    location = candidate["profile"]["location"].lower()
    country = candidate["profile"].get("country", "").lower()
    willing_to_relocate = candidate["redrob_signals"].get("willing_to_relocate", False)

    preferred = JD["preferred_locations"]
    if any(loc in location for loc in preferred):
        return 1.0
    elif "india" in country or "india" in location:
        return 0.8 if willing_to_relocate else 0.6
    else:
        return 0.3 if willing_to_relocate else 0.1


# ---------------------------------------------------------------------------
# Combined structured score
# ---------------------------------------------------------------------------

def compute_structured_score(candidate: dict) -> dict:
    """Returns a dict with all component scores and a weighted total."""
    skill_score, must_have_count, matched_skills = score_skills(candidate)
    career_score = score_career(candidate)
    exp_score = score_experience(candidate)
    edu_score = score_education(candidate)
    loc_score = score_location(candidate)

    weighted = (
        skill_score  * 0.35 +
        career_score * 0.35 +
        exp_score    * 0.15 +
        edu_score    * 0.05 +
        loc_score    * 0.10
    )

    return {
        "structured_score": round(weighted, 4),
        "skill_score": round(skill_score, 4),
        "career_score": round(career_score, 4),
        "exp_score": round(exp_score, 4),
        "edu_score": round(edu_score, 4),
        "loc_score": round(loc_score, 4),
        "must_have_skill_count": must_have_count,
        "matched_skills": matched_skills,
    }
