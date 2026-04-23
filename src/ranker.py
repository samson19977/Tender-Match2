#!/usr/bin/env python3
"""
src/ranker.py — Hybrid Tender Ranking Engine
Combines TF-IDF semantic similarity + sector match + budget fit + deadline urgency.

Scoring Formula:
  score = (0.45 * tfidf_sim) + (0.25 * sector_match) + (0.20 * budget_score) + (0.10 * urgency_score)
"""

import math
import re
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ─── Constants ───────────────────────────────────────────────────────────────
WEIGHTS = {
    "tfidf": 0.45,
    "sector": 0.25,
    "budget": 0.20,
    "urgency": 0.10,
}


# ─── Helper Functions ─────────────────────────────────────────────────────────

def sector_match_score(profile_sector: str, tender_sector: str) -> float:
    """
    Binary sector match with partial credit for related sectors.
    Returns: 1.0 (exact), 0.3 (related), 0.0 (unrelated)
    """
    if profile_sector == tender_sector:
        return 1.0
    # Related sector groups
    related_groups = [
        {"agritech", "wastetech"},   # both deal with rural/land
        {"fintech", "agritech"},     # microfinance often targets farmers
        {"edtech", "healthtech"},    # both target underserved communities
        {"cleantech", "wastetech"},  # both environmental
    ]
    for group in related_groups:
        if profile_sector in group and tender_sector in group:
            return 0.3
    return 0.0


def budget_compatibility_score(profile_max: int, tender_budget: int) -> float:
    """
    Score how well the tender budget matches the profile's needs.
    
    Logic:
    - If tender_budget == 0: unknown, give 0.5
    - If profile_max >= tender_budget: perfect fit → 1.0
    - If tender is within 2x of profile_max: partial fit → 0.5
    - If tender far exceeds profile capacity: low score
    """
    if tender_budget == 0:
        return 0.5  # Unknown budget, neutral
    if profile_max == 0:
        return 0.5
    ratio = profile_max / tender_budget
    if ratio >= 1.0:
        return 1.0   # Profile can handle this budget
    elif ratio >= 0.5:
        return 0.7   # Slightly above profile range
    elif ratio >= 0.25:
        return 0.4   # Tender much larger than profile needs
    else:
        return 0.1   # Very large mismatch


def deadline_urgency_score(deadline_str: str) -> float:
    """
    Score based on deadline proximity.
    Closer deadlines get higher urgency scores (reward relevance + timing).
    
    Returns: 0.0 – 1.0
    """
    if deadline_str == "Unknown":
        return 0.5
    
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
        # French months
        "janvier": 1, "février": 2, "mars": 3, "avril": 4,
        "mai": 5, "juin": 6, "juillet": 7, "août": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    }
    
    try:
        parts = deadline_str.split()
        if len(parts) == 3:
            day, month_name, year = parts
            month_num = month_map.get(month_name, 0)
            if month_num:
                deadline_dt = datetime(int(year), month_num, int(day))
                today = datetime.now()
                days_left = (deadline_dt - today).days
                
                if days_left < 0:
                    return 0.0   # Expired
                elif days_left <= 14:
                    return 1.0   # Very urgent
                elif days_left <= 30:
                    return 0.85
                elif days_left <= 60:
                    return 0.65
                elif days_left <= 90:
                    return 0.45
                else:
                    return 0.25  # Far future
    except Exception:
        pass
    return 0.5


def build_query(profile: dict) -> str:
    """Build a rich query string from the profile for TF-IDF matching."""
    parts = [
        profile.get("needs_text", ""),
        profile.get("sector", "") * 3,  # Boost sector weight
        profile.get("country", ""),
        profile.get("region", ""),
    ]
    return " ".join(p for p in parts if p)


# ─── Main Ranker Class ────────────────────────────────────────────────────────

class TenderRanker:
    """
    Hybrid ranking engine for tender-profile matching.
    
    Pipeline:
    1. Build TF-IDF corpus from tender texts
    2. For each profile query, compute cosine similarity
    3. Combine with sector_match + budget_score + urgency_score
    4. Return ranked list with score breakdown
    """

    def __init__(self, tenders: list):
        self.tenders = tenders
        self.vectorizer = None
        self.tfidf_matrix = None
        self._build_index()

    def _build_index(self):
        """Fit TF-IDF vectorizer on all tender documents."""
        corpus = [t["raw_text"] for t in self.tenders]
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
            analyzer="word",
            min_df=1,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        print(f"  TF-IDF index built: {self.tfidf_matrix.shape[0]} docs × {self.tfidf_matrix.shape[1]} terms")

    def rank(self, profile: dict, top_k: int = 5) -> list:
        """
        Rank tenders for a given profile.
        
        Args:
            profile: dict with keys: id, sector, budget_max, needs_text, languages
            top_k: number of results to return
            
        Returns:
            List of dicts sorted by score (descending), each with score breakdown
        """
        query = build_query(profile)
        query_vec = self.vectorizer.transform([query])
        tfidf_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        results = []
        for i, tender in enumerate(self.tenders):
            tfidf_sim = float(tfidf_scores[i])
            sector_score = sector_match_score(profile.get("sector", ""), tender.get("sector", ""))
            budget_score = budget_compatibility_score(profile.get("budget_max", 0), tender.get("budget", 0))
            urgency = deadline_urgency_score(tender.get("deadline", "Unknown"))

            # Composite score
            final_score = (
                WEIGHTS["tfidf"] * tfidf_sim +
                WEIGHTS["sector"] * sector_score +
                WEIGHTS["budget"] * budget_score +
                WEIGHTS["urgency"] * urgency
            )

            results.append({
                "tender_id": tender["id"],
                "title": tender["title"],
                "sector": tender["sector"],
                "budget": tender["budget"],
                "deadline": tender["deadline"],
                "region": tender["region"],
                "language": tender["language"],
                "score": round(final_score, 4),
                "breakdown": {
                    "tfidf_similarity": round(tfidf_sim, 4),
                    "sector_match": round(sector_score, 4),
                    "budget_score": round(budget_score, 4),
                    "urgency_score": round(urgency, 4),
                },
                "raw_text": tender["raw_text"],
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# ─── Biggest Disqualifier (Stretch Goal) ─────────────────────────────────────

def get_top_disqualifier(profile: dict, tender: dict) -> str:
    """
    Identify the single biggest reason this tender does NOT fit the profile.
    Used for the 'Why NOT this tender' stretch goal.
    """
    reasons = []

    # Deadline check
    urgency = deadline_urgency_score(tender.get("deadline", "Unknown"))
    if urgency == 0.0:
        reasons.append(("deadline", 1.0, "Deadline has already passed"))

    # Sector check
    sector_score = sector_match_score(profile.get("sector", ""), tender.get("sector", ""))
    if sector_score == 0.0:
        reasons.append(("sector", 0.9, f"Sector mismatch: profile is {profile.get('sector')}, tender targets {tender.get('sector')}"))

    # Budget check
    budget_score = budget_compatibility_score(profile.get("budget_max", 0), tender.get("budget", 0))
    if budget_score < 0.3:
        reasons.append(("budget", 0.8, f"Budget far exceeds profile capacity (tender: USD {tender.get('budget', 0):,}, profile max: USD {profile.get('budget_max', 0):,})"))

    # Region check
    profile_country = profile.get("country", "").lower()
    tender_region = tender.get("region", "").lower()
    country_region_map = {
        "rwanda": "east africa", "kenya": "east africa", "uganda": "east africa",
        "ethiopia": "east africa", "tanzania": "east africa",
        "senegal": "west africa", "ghana": "west africa", "nigeria": "west africa",
        "drc": "central africa", "cameroon": "central africa",
    }
    expected_region = country_region_map.get(profile_country, "")
    if expected_region and expected_region not in tender_region.lower() and "africa" not in tender_region.lower().replace("east africa", "").replace("west africa", "").replace("central africa", "").replace("southern africa", ""):
        reasons.append(("region", 0.7, f"Geographic mismatch: profile is in {profile.get('country')}, tender targets {tender.get('region')}"))

    if not reasons:
        return "No major disqualifier — this is a borderline match"

    # Return the most severe disqualifier
    reasons.sort(key=lambda x: x[1], reverse=True)
    return reasons[0][2]


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.insert(0, ".")
    from src.parser import load_tenders, load_profiles

    tenders = load_tenders()
    profiles = load_profiles()
    ranker = TenderRanker(tenders)

    profile = profiles[0]
    print(f"\nProfile: {profile['name']} ({profile['sector']})")
    results = ranker.rank(profile, top_k=5)
    for rank, r in enumerate(results, 1):
        print(f"  #{rank} {r['tender_id']} | score={r['score']} | {r['sector']} | {r['title'][:50]}")
        print(f"       breakdown: {r['breakdown']}")
