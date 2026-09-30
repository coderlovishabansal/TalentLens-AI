"""
Scores candidate behavioral signals from the redrob_signals object.
These signals indicate whether a candidate is actually available and responsive.
"""

from datetime import date, datetime


def parse_date(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_since(d: date | None, today: date | None = None) -> int | None:
    if d is None:
        return None
    today = today or date.today()
    return (today - d).days


def score_behavioral(candidate: dict) -> dict:
    """
    Returns behavioral score (0-1) and a breakdown.
    This is used as a MULTIPLIER on the base score, not additive.
    A perfect-on-paper candidate who is behaviorally dead gets heavily penalized.
    """
    s = candidate["redrob_signals"]
    today = date.today()

    # --- Availability ---
    open_to_work = 1.0 if s.get("open_to_work_flag", False) else 0.3

    last_active = parse_date(s.get("last_active_date"))
    inactive_days = days_since(last_active, today) or 365
    if inactive_days <= 7:
        activity_score = 1.0
    elif inactive_days <= 30:
        activity_score = 0.9
    elif inactive_days <= 90:
        activity_score = 0.7
    elif inactive_days <= 180:
        activity_score = 0.4
    else:
        activity_score = 0.1  # 6+ months inactive = probably already hired

    # --- Responsiveness ---
    response_rate = s.get("recruiter_response_rate", 0.0)  # 0-1
    response_score = response_rate  # direct use

    avg_response_hours = s.get("avg_response_time_hours", 999)
    if avg_response_hours <= 4:
        response_time_score = 1.0
    elif avg_response_hours <= 24:
        response_time_score = 0.8
    elif avg_response_hours <= 72:
        response_time_score = 0.6
    else:
        response_time_score = 0.3

    # --- Reliability ---
    interview_completion = s.get("interview_completion_rate", 0.5)
    offer_acceptance = s.get("offer_acceptance_rate", -1)
    offer_score = offer_acceptance if offer_acceptance >= 0 else 0.5  # -1 = no history

    # --- Notice period ---
    notice_days = s.get("notice_period_days", 60)
    if notice_days <= 15:
        notice_score = 1.0
    elif notice_days <= 30:
        notice_score = 0.9
    elif notice_days <= 60:
        notice_score = 0.7
    elif notice_days <= 90:
        notice_score = 0.5
    else:
        notice_score = 0.3  # 90+ day notice is painful

    # --- Platform engagement ---
    profile_views = min(s.get("profile_views_received_30d", 0) / 50, 1.0)
    saved_by_recruiters = min(s.get("saved_by_recruiters_30d", 0) / 10, 1.0)
    search_appearances = min(s.get("search_appearance_30d", 0) / 100, 1.0)

    # Platform demand signal: recruiters are already interested
    demand_score = (profile_views * 0.3 + saved_by_recruiters * 0.4 + search_appearances * 0.3)

    # --- Technical credibility ---
    github_raw = s.get("github_activity_score", -1)
    github_score = (github_raw / 100) if github_raw >= 0 else 0.3  # -1 = no github

    # --- Trust signals ---
    verified_email = 1.0 if s.get("verified_email", False) else 0.7
    verified_phone = 1.0 if s.get("verified_phone", False) else 0.8
    linkedin = 1.0 if s.get("linkedin_connected", False) else 0.85
    trust_score = (verified_email + verified_phone + linkedin) / 3

    # --- Profile completeness ---
    completeness = s.get("profile_completeness_score", 50) / 100

    # --- Weighted behavioral score ---
    behavioral = (
        open_to_work            * 0.20 +
        activity_score          * 0.20 +
        response_score          * 0.15 +
        response_time_score     * 0.05 +
        interview_completion    * 0.10 +
        offer_score             * 0.05 +
        notice_score            * 0.05 +
        demand_score            * 0.05 +
        github_score            * 0.05 +
        trust_score             * 0.05 +
        completeness            * 0.05
    )

    return {
        "behavioral_score": round(behavioral, 4),
        "open_to_work": open_to_work,
        "activity_score": round(activity_score, 4),
        "inactive_days": inactive_days,
        "response_rate": response_rate,
        "interview_completion": interview_completion,
        "notice_days": notice_days,
        "github_score": round(github_score, 4),
        "trust_score": round(trust_score, 4),
        "demand_score": round(demand_score, 4),
    }
