#!/usr/bin/env python3
"""
Synthetic Data Generator for CPI Tender Matcher
Generates 40 tender documents across EN/FR as .txt files
Run: python generate_data.py
"""

import json
import random
import os
from datetime import datetime, timedelta

random.seed(42)

SECTORS = ["agritech", "healthtech", "cleantech", "edtech", "fintech", "wastetech"]
BUDGETS = [
    ("5,000", 5000),
    ("50,000", 50000),
    ("200,000", 200000),
    ("1,000,000", 1000000),
]
REGIONS = ["East Africa", "West Africa", "Central Africa", "Southern Africa"]
COUNTRIES = ["Rwanda", "Kenya", "Uganda", "Senegal", "DRC", "Ethiopia", "Tanzania", "Ghana", "Nigeria", "Cameroon"]
ORGS = [
    "African Development Bank", "USAID", "EU Delegation", "World Bank",
    "GIZ", "UNDP", "African Union", "Bill & Melinda Gates Foundation",
    "Mastercard Foundation", "Omidyar Network"
]

EN_TEMPLATES = [
    """GRANT OPPORTUNITY: {title}

Issuing Organization: {org}
Tender Reference: TND-{ref}
Sector: {sector}
Region: {region}
Eligible Countries: {countries}

OVERVIEW
{org} invites applications from qualified organizations for the {title}. This grant supports innovative solutions in the {sector} space across {region}.

BUDGET
Total available funding: USD {budget_str}
Maximum grant per applicant: USD {max_grant}

ELIGIBILITY
- Registered organizations operating in {region}
- Minimum {min_employees} full-time employees
- At least 1 year of operational history
- Prior funding experience preferred: {prior_funding}

OBJECTIVES
This tender aims to:
1. Accelerate {sector} innovation in underserved communities
2. Support scalable and sustainable business models
3. Foster cross-border collaboration in {region}
4. Promote gender inclusion and youth employment

APPLICATION REQUIREMENTS
Applicants must submit:
- Technical proposal (max 15 pages)
- Budget breakdown
- Organizational profile
- Letters of support from local partners

DEADLINE
Application deadline: {deadline}
Results announcement: {result_date}

CONTACT
For inquiries, contact: grants@{org_email}.org
Reference: {ref}
""",

    """FUNDING CALL: {title}

Reference Number: FC-{ref}
Funding Body: {org}
Focus Area: {sector}
Target Geography: {region}

BACKGROUND
Access to {sector} solutions remains limited across {region}. {org} is committed to bridging this gap through targeted grant support.

GRANT DETAILS
- Total envelope: USD {budget_str}
- Individual awards: up to USD {max_grant}
- Duration: 12–24 months

WHO CAN APPLY
Eligible applicants include:
• Social enterprises and cooperatives in {countries}
• NGOs with a proven track record in {sector}
• University spin-offs and research centres
• Minimum team size: {min_employees} employees

EVALUATION CRITERIA
Applications will be scored on:
- Innovation and scalability (30%)
- Impact on underserved populations (25%)
- Financial sustainability (20%)
- Team capability (15%)
- Regional relevance (10%)

KEY DATES
Submission deadline: {deadline}
Interview round: {result_date}

SUBMIT AT: apply.{org_email}.org/FC-{ref}
"""
]

FR_TEMPLATES = [
    """APPEL À CANDIDATURES : {title}

Organisme émetteur : {org}
Référence : TND-{ref}
Secteur : {sector}
Région : {region}
Pays éligibles : {countries}

PRÉSENTATION
{org} lance un appel à candidatures pour le {title}. Ce financement soutient des solutions innovantes dans le domaine {sector} à travers {region}.

BUDGET
Enveloppe totale disponible : USD {budget_str}
Subvention maximale par candidat : USD {max_grant}

ÉLIGIBILITÉ
- Organisations enregistrées opérant en {region}
- Au moins {min_employees} employés à temps plein
- Au moins 1 an d'existence
- Expérience de financement antérieure souhaitée : {prior_funding}

OBJECTIFS
Cet appel vise à :
1. Accélérer l'innovation {sector} dans les communautés mal desservies
2. Soutenir des modèles économiques évolutifs et durables
3. Favoriser la coopération transfrontalière en {region}
4. Promouvoir l'inclusion des femmes et l'emploi des jeunes

DOSSIER DE CANDIDATURE
Les candidats doivent soumettre :
- Proposition technique (15 pages max)
- Détail budgétaire
- Profil organisationnel
- Lettres de soutien de partenaires locaux

DATE LIMITE
Date de soumission : {deadline}
Annonce des résultats : {result_date}

CONTACT
Pour toute question : subventions@{org_email}.org
Référence : {ref}
""",

    """APPEL À PROJETS : {title}

Numéro de référence : AP-{ref}
Bailleur de fonds : {org}
Domaine prioritaire : {sector}
Zone géographique : {region}

CONTEXTE
L'accès aux solutions {sector} reste limité dans {region}. {org} s'engage à combler ce fossé grâce à un soutien ciblé.

DÉTAILS DU FINANCEMENT
- Enveloppe totale : USD {budget_str}
- Subventions individuelles : jusqu'à USD {max_grant}
- Durée : 12 à 24 mois

QUI PEUT CANDIDATER
Les candidats éligibles comprennent :
• Entreprises sociales et coopératives en {countries}
• ONG avec un historique prouvé dans {sector}
• Start-ups universitaires et centres de recherche
• Taille minimale de l'équipe : {min_employees} employés

CRITÈRES D'ÉVALUATION
Les dossiers seront notés sur :
- Innovation et capacité à l'échelle (30%)
- Impact sur les populations mal desservies (25%)
- Viabilité financière (20%)
- Compétences de l'équipe (15%)
- Pertinence régionale (10%)

CALENDRIER
Date limite de soumission : {deadline}
Entretiens : {result_date}

SOUMISSION : candidatures.{org_email}.org/AP-{ref}
"""
]

SECTOR_TITLES_EN = {
    "agritech": ["Digital Agriculture Innovation Grant", "Precision Farming Support Fund", "Smallholder AgriTech Scale-Up Grant", "Agricultural Digitization Challenge"],
    "healthtech": ["Rural Health Technology Grant", "Community Health Innovation Fund", "Digital Health Access Programme", "Telemedicine Expansion Grant"],
    "cleantech": ["Clean Energy Access Fund", "Renewable Energy Scale-Up Grant", "Green Technology Innovation Award", "Solar Solutions Deployment Grant"],
    "edtech": ["Digital Learning Innovation Fund", "EdTech for Inclusion Grant", "Offline Education Technology Grant", "Rural Digital Literacy Programme"],
    "fintech": ["Financial Inclusion Innovation Grant", "Digital Finance Scale-Up Fund", "Cooperative Finance Technology Grant", "Mobile Money Expansion Award"],
    "wastetech": ["Circular Economy Innovation Grant", "Waste-to-Value Technology Fund", "Sustainable Waste Management Grant", "Biogas and Composting Scale-Up"]
}

SECTOR_TITLES_FR = {
    "agritech": ["Subvention pour l'Innovation Agricole Numérique", "Fonds de Soutien à l'Agriculture de Précision", "Programme AgriTech pour Petits Exploitants"],
    "healthtech": ["Subvention Technologie Santé Rurale", "Fonds Innovation Santé Communautaire", "Programme de Télémédecine Rurale"],
    "cleantech": ["Fonds d'Accès à l'Énergie Propre", "Subvention Énergie Renouvelable", "Prix Innovation Technologie Verte"],
    "edtech": ["Fonds Innovation Apprentissage Numérique", "Subvention EdTech pour l'Inclusion", "Programme Éducation Hors-Ligne"],
    "fintech": ["Subvention Inclusion Financière", "Fonds Finance Numérique", "Programme Finance Coopérative Mobile"],
    "wastetech": ["Subvention Économie Circulaire", "Fonds Valorisation des Déchets", "Programme Biogaz et Compostage"]
}


def random_deadline(days_min=30, days_max=120):
    future = datetime.now() + timedelta(days=random.randint(days_min, days_max))
    return future.strftime("%d %B %Y")


def random_result_date(deadline_str):
    deadline = datetime.strptime(deadline_str, "%d %B %Y")
    result = deadline + timedelta(days=random.randint(30, 60))
    return result.strftime("%d %B %Y")


def generate_tender(tender_id, lang, sector, budget_tuple):
    budget_str, budget_val = budget_tuple
    max_grant = budget_val // 2
    is_fr = lang == "fr"

    if is_fr:
        title = random.choice(SECTOR_TITLES_FR[sector])
        template = random.choice(FR_TEMPLATES)
    else:
        title = random.choice(SECTOR_TITLES_EN[sector])
        template = random.choice(EN_TEMPLATES)

    org = random.choice(ORGS)
    region = random.choice(REGIONS)
    countries = ", ".join(random.sample(COUNTRIES, 3))
    min_employees = random.choice([3, 5, 10, 15])
    prior_funding = random.choice(["Not required", "Preferred", "Required"])
    deadline = random_deadline()
    result_date = random_result_date(deadline)
    org_email = org.lower().replace(" ", "").replace("&", "and")[:15]
    ref = f"{tender_id:03d}{random.randint(100,999)}"

    content = template.format(
        title=title,
        org=org,
        ref=ref,
        sector=sector,
        region=region,
        countries=countries,
        budget_str=budget_str,
        max_grant=f"{max_grant:,}",
        min_employees=min_employees,
        prior_funding=prior_funding,
        deadline=deadline,
        result_date=result_date,
        org_email=org_email
    )

    return {
        "id": f"T{tender_id:03d}",
        "title": title,
        "sector": sector,
        "budget": budget_val,
        "deadline": deadline,
        "region": region,
        "language": lang,
        "content": content
    }


def main():
    os.makedirs("data/tenders", exist_ok=True)
    tenders = []
    tender_id = 1

    # Generate 40 tenders: 60% EN, 40% FR
    # Ensure each sector has tenders in both languages
    plan = []
    for sector in SECTORS:
        for budget in BUDGETS[:2]:  # 2 budgets per sector = 12 EN
            plan.append(("en", sector, budget))
    for sector in SECTORS:
        for budget in BUDGETS[2:]:  # 2 budgets per sector = 12 FR ... adjust
            plan.append(("fr", sector, budget))
    # Add 16 more EN tenders for 60/40 split
    extras_en = []
    for sector in random.choices(SECTORS, k=8):
        extras_en.append(("en", sector, random.choice(BUDGETS)))
    extras_fr = []
    for sector in random.choices(SECTORS, k=4):
        extras_fr.append(("fr", sector, random.choice(BUDGETS)))

    plan = plan + extras_en + extras_fr
    random.shuffle(plan)
    plan = plan[:40]

    for lang, sector, budget in plan:
        tender = generate_tender(tender_id, lang, sector, budget)
        tenders.append(tender)
        fname = f"data/tenders/{tender['id']}_{lang}_{sector}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(tender["content"])
        print(f"  Generated: {fname}")
        tender_id += 1

    # Save metadata
    meta = [{k: v for k, v in t.items() if k != "content"} for t in tenders]
    with open("data/tenders_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Generate gold_matches.csv (3 expert matches per profile)
    profiles = json.load(open("data/profiles.json"))
    gold_rows = ["profile_id,tender_id,rank"]

    sector_to_tenders = {}
    for t in tenders:
        sector_to_tenders.setdefault(t["sector"], []).append(t["id"])

    for p in profiles:
        sector = p["sector"]
        candidates = sector_to_tenders.get(sector, [])
        if len(candidates) < 3:
            # fallback: any tender
            candidates = [t["id"] for t in tenders]
        chosen = random.sample(candidates, min(3, len(candidates)))
        for rank, tid in enumerate(chosen, 1):
            gold_rows.append(f"{p['id']},{tid},{rank}")

    with open("data/gold_matches.csv", "w") as f:
        f.write("\n".join(gold_rows))

    print(f"\n✅ Generated {len(tenders)} tenders in data/tenders/")
    print(f"✅ Saved data/tenders_meta.json")
    print(f"✅ Saved data/gold_matches.csv")


if __name__ == "__main__":
    main()
