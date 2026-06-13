def score_profile(profile: dict) -> dict:
    """
    Pure deterministic scoring. No LLM involved.
    Returns score 0-100 with per-category breakdown.
    """
    score = 0
    breakdown = {}

    # GPA (0–40 points)
    gpa_norm = float(profile["gpa"]) / float(profile.get("gpa_scale", 4.0))
    if gpa_norm >= 0.90:    gpa_pts = 40
    elif gpa_norm >= 0.80:  gpa_pts = 32
    elif gpa_norm >= 0.70:  gpa_pts = 22
    elif gpa_norm >= 0.60:  gpa_pts = 12
    else:                   gpa_pts = 4
    breakdown["gpa"] = gpa_pts
    score += gpa_pts

    # IELTS (0–30 points)
    ielts = float(profile.get("ielts_overall") or 0)
    if ielts >= 7.5:    ielts_pts = 30
    elif ielts >= 7.0:  ielts_pts = 24
    elif ielts >= 6.5:  ielts_pts = 18
    elif ielts >= 6.0:  ielts_pts = 10
    else:               ielts_pts = 3
    breakdown["ielts"] = ielts_pts
    score += ielts_pts

    # Financial proof (0–20 points)
    fin = int(profile.get("financial_proof_usd") or 0)
    if fin >= 2000:     fin_pts = 20
    elif fin >= 1500:   fin_pts = 15
    elif fin >= 1000:   fin_pts = 10
    elif fin >= 500:    fin_pts = 5
    else:               fin_pts = 0
    breakdown["financial"] = fin_pts
    score += fin_pts

    # Experience (0–10 points)
    work = int(profile.get("work_experience_months") or 0)
    gap  = int(profile.get("gap_years") or 0)
    exp_pts = max(0, min(10, work // 6 * 3 - gap * 2))
    breakdown["experience"] = exp_pts
    score += exp_pts

    return {
        "total": score,
        "breakdown": breakdown,
        "band": _band(score),
    }


def _band(score: int) -> str:
    if score >= 80:  return "Strong"
    if score >= 60:  return "Moderate"
    if score >= 40:  return "Weak"
    return "Not viable"


def match_universities(profile: dict, universities: list) -> list:
    """
    Filter and score universities against student profile.
    Returns list with match_score appended, sorted descending.
    """
    matched = []
    for uni in universities:
        ok, match_score = _evaluate_match(profile, uni)
        if ok:
            uni_dict = dict(uni.__dict__) if hasattr(uni, "__dict__") else uni
            uni_dict["match_score"] = match_score
            matched.append(uni_dict)
    return sorted(matched, key=lambda u: u["match_score"], reverse=True)


def _evaluate_match(profile: dict, uni) -> tuple[bool, int]:
    score = 100

    gpa     = float(profile.get("gpa") or 0)
    ielts   = float(profile.get("ielts_overall") or 0)
    budget  = int(profile.get("budget_usd_per_year") or 0)
    gap     = int(profile.get("gap_years") or 0)

    min_gpa   = float(uni.min_gpa or 0)
    min_ielts = float(uni.min_ielts or 0)
    tuition   = int(uni.annual_tuition_usd or 0)

    # Hard filters
    if min_gpa and gpa < min_gpa:
        return False, 0
    if min_ielts and ielts < min_ielts:
        return False, 0
    if not uni.accepts_gap_years and gap > 0:
        return False, 0

    # Soft scoring
    if gpa > min_gpa + 0.5:
        score += 10
    if ielts > min_ielts + 0.5:
        score += 10
    if budget and tuition and tuition > budget:
        score -= 20
    if uni.visa_approval_rate_pct and uni.visa_approval_rate_pct >= 80:
        score += 5

    return True, max(0, min(100, score))
