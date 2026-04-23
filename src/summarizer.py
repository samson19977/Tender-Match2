#!/usr/bin/env python3
"""
src/summarizer.py — Match Explanation Generator
Generates ≤80-word explanations in EN or FR explaining why a tender matches a profile.
Uses template-based generation (CPU-only, no LLM dependency required).
"""

import random

# ─── English Templates ────────────────────────────────────────────────────────
EN_TEMPLATES = [
    (
        "{org_name} matches **{tender_title}** (score: {score:.2f}). "
        "This {sector} grant from {tender_region} aligns with your operations in {country}. "
        "The available funding of USD {budget:,} fits your budget range. "
        "Deadline: {deadline}. "
        "Sector overlap and {tfidf_pct}% content similarity drive this ranking."
    ),
    (
        "**{tender_title}** is ranked #{rank} for {org_name}. "
        "Sector: {sector} ✓. Budget: USD {budget:,}. Deadline: {deadline}. "
        "Your needs in {needs_snippet} closely match this tender's objectives. "
        "Score breakdown — similarity: {tfidf_pct}%, sector: {sector_pct}%, budget: {budget_pct}%."
    ),
    (
        "This {sector} opportunity suits {org_name} because your profile in {country} aligns "
        "with the tender's focus on {region_phrase}. "
        "Budget of USD {budget:,} is within reach. Apply before {deadline}. "
        "Composite match score: {score:.2f}/1.00."
    ),
]

# ─── French Templates ─────────────────────────────────────────────────────────
FR_TEMPLATES = [
    (
        "{org_name} correspond à **{tender_title}** (score : {score:.2f}). "
        "Cette subvention {sector} en {tender_region} s'aligne avec vos activités en {country}. "
        "Le financement disponible de USD {budget:,} correspond à votre capacité budgétaire. "
        "Date limite : {deadline}. "
        "La correspondance sectorielle et {tfidf_pct}% de similarité de contenu motivent ce classement."
    ),
    (
        "**{tender_title}** est classé #{rank} pour {org_name}. "
        "Secteur : {sector} ✓. Budget : USD {budget:,}. Date limite : {deadline}. "
        "Vos besoins en {needs_snippet} correspondent étroitement aux objectifs de cet appel. "
        "Détail du score — similarité : {tfidf_pct}%, secteur : {sector_pct}%, budget : {budget_pct}%."
    ),
    (
        "Cette opportunité {sector} convient à {org_name} car votre profil en {country} s'aligne "
        "avec l'appel ciblant {region_phrase}. "
        "Le budget de USD {budget:,} est accessible. Déposez votre candidature avant le {deadline}. "
        "Score composite : {score:.2f}/1.00."
    ),
]

SECTOR_PHRASES_EN = {
    "agritech": "digital agriculture and farming innovation",
    "healthtech": "health technology and community health services",
    "cleantech": "clean and renewable energy solutions",
    "edtech": "digital education and offline learning",
    "fintech": "digital finance and financial inclusion",
    "wastetech": "waste management and circular economy",
    "general": "general development and innovation",
}

SECTOR_PHRASES_FR = {
    "agritech": "l'agriculture numérique et l'innovation agricole",
    "healthtech": "la technologie de santé et les services de santé communautaire",
    "cleantech": "les solutions d'énergie propre et renouvelable",
    "edtech": "l'éducation numérique et l'apprentissage hors-ligne",
    "fintech": "la finance numérique et l'inclusion financière",
    "wastetech": "la gestion des déchets et l'économie circulaire",
    "general": "le développement général et l'innovation",
}

REGION_PHRASES_EN = {
    "East Africa": "East African markets",
    "West Africa": "West African communities",
    "Central Africa": "Central African regions",
    "Southern Africa": "Southern African areas",
    "Africa": "pan-African initiatives",
}

REGION_PHRASES_FR = {
    "East Africa": "les marchés d'Afrique de l'Est",
    "West Africa": "les communautés d'Afrique de l'Ouest",
    "Central Africa": "les régions d'Afrique Centrale",
    "Southern Africa": "les zones d'Afrique Australe",
    "Africa": "les initiatives panafricaines",
}


def _truncate_to_words(text: str, max_words: int = 80) -> str:
    """Truncate text to max_words, ending at a sentence boundary if possible."""
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    # Try to end at last sentence
    for punct in [".", "!", "?"]:
        idx = truncated.rfind(punct)
        if idx > len(truncated) // 2:
            return truncated[:idx + 1]
    return truncated + "..."


def generate_summary(
    profile: dict,
    tender: dict,
    rank: int,
    score: float,
    breakdown: dict,
    language: str = "en",
    max_words: int = 80,
) -> str:
    """
    Generate a ≤80-word explanation of why this tender matches the profile.
    
    Args:
        profile: business profile dict
        tender: matched tender dict
        rank: rank position (1–5)
        score: composite match score (0–1)
        breakdown: dict with tfidf_similarity, sector_match, budget_score, urgency_score
        language: "en" or "fr"
        max_words: word limit (default 80)
    
    Returns:
        Formatted explanation string
    """
    lang = language if language in ["en", "fr"] else "en"

    # Derived values
    tfidf_pct = int(breakdown.get("tfidf_similarity", 0) * 100)
    sector_pct = int(breakdown.get("sector_match", 0) * 100)
    budget_pct = int(breakdown.get("budget_score", 0) * 100)
    urgency_pct = int(breakdown.get("urgency_score", 0) * 100)

    sector = tender.get("sector", "general")
    region = tender.get("region", "Africa")
    needs_text = profile.get("needs_text", "")
    needs_snippet = " ".join(needs_text.split()[:6]) + "..." if needs_text else "various areas"

    if lang == "fr":
        templates = FR_TEMPLATES
        region_phrase = REGION_PHRASES_FR.get(region, "les régions africaines")
    else:
        templates = EN_TEMPLATES
        region_phrase = REGION_PHRASES_EN.get(region, "African regions")

    template = templates[rank % len(templates)]

    summary = template.format(
        org_name=profile.get("name", "Your organization"),
        tender_title=tender.get("title", "This Tender"),
        score=score,
        sector=sector,
        country=profile.get("country", "your country"),
        budget=tender.get("budget", 0),
        deadline=tender.get("deadline", "TBD"),
        tfidf_pct=tfidf_pct,
        sector_pct=sector_pct,
        budget_pct=budget_pct,
        urgency_pct=urgency_pct,
        rank=rank,
        needs_snippet=needs_snippet,
        tender_region=region,
        region_phrase=region_phrase,
    )

    return _truncate_to_words(summary, max_words)


def generate_summary_md(
    profile: dict,
    matches: list,
    language: str = "en",
) -> str:
    """
    Generate a complete markdown summary file for all matches of a profile.
    
    Args:
        profile: business profile dict
        matches: list of ranked tender dicts (from ranker.rank())
        language: "en" or "fr"
    
    Returns:
        Full markdown string
    """
    lang = language if language in ["en", "fr"] else "en"
    lines = []

    if lang == "fr":
        lines.append(f"# Correspondances de Subventions — {profile.get('name', 'Profil')}")
        lines.append(f"\n**Profil :** {profile.get('name')} | **Secteur :** {profile.get('sector')} | **Pays :** {profile.get('country')}")
        lines.append(f"\n**Besoins :** {profile.get('needs_text', '')}\n")
        lines.append("---\n")
        lines.append("## Top 5 Appels à Candidatures\n")
    else:
        lines.append(f"# Grant Matches — {profile.get('name', 'Profile')}")
        lines.append(f"\n**Profile:** {profile.get('name')} | **Sector:** {profile.get('sector')} | **Country:** {profile.get('country')}")
        lines.append(f"\n**Needs:** {profile.get('needs_text', '')}\n")
        lines.append("---\n")
        lines.append("## Top 5 Matched Tenders\n")

    for rank, match in enumerate(matches, 1):
        score = match["score"]
        breakdown = match["breakdown"]

        summary = generate_summary(
            profile=profile,
            tender=match,
            rank=rank,
            score=score,
            breakdown=breakdown,
            language=lang,
        )

        if lang == "fr":
            lines.append(f"### #{rank} — {match['title']}")
            lines.append(f"**ID :** {match['tender_id']} | **Score :** {score:.4f} | **Langue :** {match['language'].upper()}")
            lines.append(f"\n**Explication :**\n{summary}\n")
            lines.append(f"**Détail du score :**")
            lines.append(f"- Similarité TF-IDF : {breakdown['tfidf_similarity']:.3f}")
            lines.append(f"- Correspondance sectorielle : {breakdown['sector_match']:.3f}")
            lines.append(f"- Compatibilité budgétaire : {breakdown['budget_score']:.3f}")
            lines.append(f"- Urgence deadline : {breakdown['urgency_score']:.3f}\n")
        else:
            lines.append(f"### #{rank} — {match['title']}")
            lines.append(f"**ID:** {match['tender_id']} | **Score:** {score:.4f} | **Language:** {match['language'].upper()}")
            lines.append(f"\n**Explanation:**\n{summary}\n")
            lines.append(f"**Score Breakdown:**")
            lines.append(f"- TF-IDF Similarity: {breakdown['tfidf_similarity']:.3f}")
            lines.append(f"- Sector Match: {breakdown['sector_match']:.3f}")
            lines.append(f"- Budget Compatibility: {breakdown['budget_score']:.3f}")
            lines.append(f"- Deadline Urgency: {breakdown['urgency_score']:.3f}\n")

        lines.append("---\n")

    return "\n".join(lines)


def generate_individual_summary_md(
    profile: dict,
    match: dict,
    rank: int,
    language: str = "en",
    disqualifier: str = "",
) -> str:
    """
    Generate a single .md file for one (profile, tender) match pair.
    Spec requires one .md per (profile, tender) match in summaries/.

    Args:
        profile: business profile dict
        match: single ranked tender dict (from ranker.rank())
        rank: rank position (1-based)
        language: "en" or "fr"
        disqualifier: pre-computed top disqualifier string

    Returns:
        Markdown string for this individual match
    """
    from src.utils import format_budget

    lang = language if language in ["en", "fr"] else "en"
    score = match["score"]
    breakdown = match["breakdown"]
    tid = match["tender_id"]

    summary_text = generate_summary(
        profile=profile,
        tender=match,
        rank=rank,
        score=score,
        breakdown=breakdown,
        language=lang,
    )

    budget_str = format_budget(match.get("budget", 0))
    disq = disqualifier or "No major disqualifier identified."

    if lang == "fr":
        return (
            f"# {match['title']}\n"
            f"**Profil :** {profile.get('name')} | **ID :** {profile.get('id')} "
            f"| **Langue :** {lang.upper()}\n\n"
            "---\n\n"
            f"## Résumé de Correspondance (#{rank})\n\n"
            f"{summary_text}\n\n"
            "---\n\n"
            "## Détails\n\n"
            "| Champ | Valeur |\n|-------|--------|\n"
            f"| ID Appel | {tid} |\n"
            f"| Score Composite | {score:.4f} |\n"
            f"| Secteur | {match['sector']} |\n"
            f"| Budget | {budget_str} |\n"
            f"| Date Limite | {match['deadline']} |\n"
            f"| Région | {match['region']} |\n"
            f"| Langue du Document | {match['language'].upper()} |\n\n"
            "## Détail du Score\n\n"
            "| Composant | Score |\n|-----------|-------|\n"
            f"| Similarité TF-IDF | {breakdown['tfidf_similarity']:.3f} |\n"
            f"| Correspondance Sectorielle | {breakdown['sector_match']:.3f} |\n"
            f"| Compatibilité Budgétaire | {breakdown['budget_score']:.3f} |\n"
            f"| Urgence Deadline | {breakdown['urgency_score']:.3f} |\n\n"
            f"## ⚠ Principal Facteur Disqualifiant\n\n{disq}\n"
        )
    else:
        return (
            f"# {match['title']}\n"
            f"**Profile:** {profile.get('name')} | **ID:** {profile.get('id')} "
            f"| **Language:** {lang.upper()}\n\n"
            "---\n\n"
            f"## Match Summary (#{rank})\n\n"
            f"{summary_text}\n\n"
            "---\n\n"
            "## Details\n\n"
            "| Field | Value |\n|-------|-------|\n"
            f"| Tender ID | {tid} |\n"
            f"| Composite Score | {score:.4f} |\n"
            f"| Sector | {match['sector']} |\n"
            f"| Budget | {budget_str} |\n"
            f"| Deadline | {match['deadline']} |\n"
            f"| Region | {match['region']} |\n"
            f"| Document Language | {match['language'].upper()} |\n\n"
            "## Score Breakdown\n\n"
            "| Component | Score |\n|-----------|-------|\n"
            f"| TF-IDF Similarity | {breakdown['tfidf_similarity']:.3f} |\n"
            f"| Sector Match | {breakdown['sector_match']:.3f} |\n"
            f"| Budget Compatibility | {breakdown['budget_score']:.3f} |\n"
            f"| Deadline Urgency | {breakdown['urgency_score']:.3f} |\n\n"
            f"## ⚠ Biggest Disqualifier\n\n{disq}\n"
        )


if __name__ == "__main__":
    # Quick test
    profile = {
        "id": "01", "name": "AgriGrow Rwanda", "sector": "agritech",
        "country": "Rwanda", "budget_max": 50000,
        "needs_text": "We need funding to scale our precision farming app.",
        "languages": ["en"]
    }
    tender = {
        "id": "T004", "title": "Digital Agriculture Innovation Grant",
        "sector": "agritech", "budget": 50000, "deadline": "15 August 2025",
        "region": "East Africa", "language": "en"
    }
    breakdown = {"tfidf_similarity": 0.45, "sector_match": 1.0, "budget_score": 1.0, "urgency_score": 0.65}
    
    print("=== EN Summary ===")
    print(generate_summary(profile, tender, 1, 0.78, breakdown, "en"))
    print("\n=== FR Summary ===")
    print(generate_summary(profile, tender, 1, 0.78, breakdown, "fr"))
