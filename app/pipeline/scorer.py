"""
Scorer: ranks and filters scraped jobs against a user's target profile.

Adapted from the original job-search-pipeline job_scorer.py.
Each job gets a score (0-100) and a pass/fail flag.
"""

import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Seniority keywords that indicate executive-level roles
SENIORITY_KEYWORDS = [
    "cto", "chief technology officer", "cdo", "chief data officer",
    "vp engineering", "vp of engineering", "head of technology",
    "head of tech", "director of technology", "director of engineering",
    "chief", "vp ", "head of", "director",
]

# Red-flag terms that indicate junior/mid-level roles
JUNIOR_KEYWORDS = [
    "junior", "graduate", "intern", "trainee", "entry level",
    "junior developer", "apprentice",
]


def score_jobs(
    jobs: List[Dict],
    target_titles: List[str],
    salary_min: int = 0,
    salary_max: Optional[int] = None,
    exclusions: Optional[List[str]] = None,
) -> List[Dict]:
    """Score and filter a list of job dicts.

    Adds keys: score (float), pass (bool), fit_notes (str).
    Returns the same list with these keys populated.
    """
    exclusions = [e.lower().strip() for e in (exclusions or [])]

    for job in jobs:
        score = 0.0
        notes = []
        title_lower = (job.get("title") or "").lower()
        company_lower = (job.get("company") or "").lower()
        combined_text = f"{title_lower} {company_lower} {job.get('description') or ''}"

        # --- Exclusion check ---
        excluded = False
        for ex in exclusions:
            if ex and ex in company_lower:
                job["score"] = 0.0
                job["pass"] = False
                job["fit_notes"] = f"Excluded company: {ex}"
                excluded = True
                break
        if excluded:
            continue

        # --- Title match ---
        title_match = False
        for target in target_titles:
            target_lower = target.lower().strip()
            if target_lower in title_lower:
                score += 30
                title_match = True
                notes.append("Title match")
                break

        if not title_match:
            # Check for seniority keywords
            for kw in SENIORITY_KEYWORDS:
                if kw in title_lower:
                    score += 15
                    notes.append(f"Seniority keyword: {kw.strip()}")
                    title_match = True
                    break

        if not title_match:
            score += 0
            notes.append("No title match")

        # --- Junior filter ---
        for kw in JUNIOR_KEYWORDS:
            if kw in title_lower:
                score -= 25
                notes.append(f"Junior keyword: {kw}")
                break

        # --- Salary check ---
        salary_str = job.get("salary") or ""
        if salary_str:
            salary_val = _extract_salary(salary_str)
            if salary_val:
                if salary_min and salary_val < salary_min:
                    score -= 20
                    notes.append(f"Salary below floor ({salary_val} < {salary_min})")
                else:
                    score += 15
                    notes.append("Salary in range")
                if salary_max and salary_val > salary_max:
                    score -= 10
                    notes.append("Salary above ceiling")

        # --- Location bonus ---
        location = (job.get("location") or "").lower()
        if "london" in location or "remote" in location:
            score += 10
            notes.append("Good location")

        # --- Clamp score ---
        score = max(0, min(100, score))

        job["score"] = round(score, 1)
        job["pass"] = score >= 25  # minimum threshold
        job["fit_notes"] = "; ".join(notes)

    return jobs


def _extract_salary(salary_str: str) -> Optional[int]:
    """Extract a numeric salary value from a salary string (returns lower bound)."""
    # Look for patterns like £150,000 or 150k or $200,000
    match = re.search(r'[\£\$\€]\s*(\d{2,3})(?:,?(\d{3}))*k?', salary_str, re.IGNORECASE)
    if match:
        # Reconstruct the number
        nums = [g for g in match.groups() if g]
        if nums:
            first = int(nums[0])
            if first < 100:
                # Probably like "150k" — multiply
                if "k" in salary_str.lower():
                    return first * 1000
            else:
                # Reconstruct from comma-separated groups
                full = int("".join(nums))
                return full

    # Fallback: just grab any number followed by k
    match = re.search(r'(\d{2,3})k', salary_str, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 1000

    return None
