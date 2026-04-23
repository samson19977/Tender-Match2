#!/usr/bin/env python3
"""
src/parser.py — Tender Document Parser
Handles .txt, .html, .pdf files and extracts structured fields.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime


def detect_language(text: str) -> str:
    """Simple rule-based language detection (FR vs EN). CPU-only, no deps."""
    fr_words = ["pour", "dans", "nous", "les", "des", "une", "est", "avec",
                "financ", "candid", "subvention", "appel", "projet", "éligib"]
    en_words = ["for", "the", "and", "with", "grant", "funding", "applicants",
                "eligible", "organization", "support", "submit", "proposal"]
    text_lower = text.lower()
    fr_count = sum(1 for w in fr_words if w in text_lower)
    en_count = sum(1 for w in en_words if w in text_lower)
    return "fr" if fr_count > en_count else "en"


def extract_budget(text: str) -> int:
    """Extract the largest budget figure from text."""
    patterns = [
        r'USD\s*([\d,]+)',
        r'\$([\d,]+)',
        r'([\d,]+)\s*USD',
        r'([\d,.]+)\s*million',
    ]
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            try:
                val = m.replace(",", "").replace(".", "")
                amounts.append(int(val))
            except ValueError:
                pass
    # Handle 'million'
    mil_matches = re.findall(r'([\d.]+)\s*million', text, re.IGNORECASE)
    for m in mil_matches:
        try:
            amounts.append(int(float(m) * 1_000_000))
        except ValueError:
            pass
    return max(amounts) if amounts else 0


def extract_deadline(text: str) -> str:
    """Extract application deadline date."""
    patterns = [
        r'[Dd]eadline[:\s]+([0-9]{1,2}\s+\w+\s+202[0-9])',
        r'[Dd]ate limite[:\s]+([0-9]{1,2}\s+\w+\s+202[0-9])',
        r'[Ss]ubmission[:\s]+([0-9]{1,2}\s+\w+\s+202[0-9])',
        r'[Ss]oumission[:\s]+([0-9]{1,2}\s+\w+\s+202[0-9])',
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    return "Unknown"


def extract_sector(text: str, filename: str = "") -> str:
    """Extract sector from content or filename."""
    sectors = ["agritech", "healthtech", "cleantech", "edtech", "fintech", "wastetech"]
    # Try filename first
    for s in sectors:
        if s in filename.lower():
            return s
    # Try content
    text_lower = text.lower()
    sector_keywords = {
        "agritech": ["agri", "farming", "agriculture", "crop", "smallholder"],
        "healthtech": ["health", "santé", "medical", "téléméde", "clinic"],
        "cleantech": ["clean", "solar", "energy", "renewable", "énergie"],
        "edtech": ["educat", "learn", "school", "digital literacy", "tablet"],
        "fintech": ["finance", "microloan", "mobile money", "credit", "saving"],
        "wastetech": ["waste", "biogas", "compost", "circular", "déchets"],
    }
    scores = {s: 0 for s in sectors}
    for sector, keywords in sector_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                scores[sector] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def extract_region(text: str) -> str:
    """Extract target region from text."""
    regions = {
        "East Africa": ["east africa", "rwanda", "kenya", "uganda", "ethiopia", "tanzania"],
        "West Africa": ["west africa", "senegal", "ghana", "nigeria", "mali", "côte d'ivoire"],
        "Central Africa": ["central africa", "drc", "cameroon", "congo", "kinshasa"],
        "Southern Africa": ["southern africa", "zambia", "zimbabwe", "mozambique", "malawi"],
    }
    text_lower = text.lower()
    for region, keywords in regions.items():
        if any(kw in text_lower for kw in keywords):
            return region
    return "Africa"


def extract_title(text: str, filename: str = "") -> str:
    """Extract tender title from first meaningful line."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:5]:
        # Skip boilerplate headers
        if len(line) > 10 and not line.startswith("#") and ":" not in line[:3]:
            # Clean common prefixes
            for prefix in ["GRANT OPPORTUNITY:", "FUNDING CALL:", "APPEL À CANDIDATURES :", "APPEL À PROJETS :"]:
                if line.startswith(prefix):
                    return line[len(prefix):].strip()
            return line
    # Fallback: derive from filename
    return Path(filename).stem.replace("_", " ").title() if filename else "Unknown Tender"


def parse_txt(filepath: str) -> dict:
    """Parse a .txt tender file."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return text


def parse_html(filepath: str) -> dict:
    """Parse an .html tender file (strip tags)."""
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()
    # Simple tag stripper
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_file(filepath: str) -> dict:
    """
    Parse any supported file format and return a structured tender record.
    
    Returns:
        dict with keys: id, title, sector, budget, deadline, region, language, raw_text, filepath
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == ".txt":
        text = parse_txt(filepath)
    elif ext in [".html", ".htm"]:
        text = parse_html(filepath)
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
        except ImportError:
            # Fallback: try pdftotext CLI if pypdf not installed
            try:
                import subprocess
                result = subprocess.run(["pdftotext", filepath, "-"], capture_output=True, text=True)
                text = result.stdout if result.returncode == 0 else ""
            except Exception:
                text = ""
        except Exception as e:
            text = ""
        if not text.strip():
            text = f"[PDF: {path.name} — text extraction failed, file may be scanned/image-based]"
    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    tender_id = path.stem.split("_")[0] if "_" in path.stem else path.stem

    return {
        "id": tender_id,
        "title": extract_title(text, path.name),
        "sector": extract_sector(text, path.name),
        "budget": extract_budget(text),
        "deadline": extract_deadline(text),
        "region": extract_region(text),
        "language": detect_language(text),
        "raw_text": text,
        "filepath": str(filepath)
    }


def load_tenders(tenders_dir: str = "data/tenders") -> list:
    """Load and parse all tender documents from a directory."""
    tenders = []
    supported = {".txt", ".html", ".htm", ".pdf"}
    for fpath in sorted(Path(tenders_dir).iterdir()):
        if fpath.suffix.lower() in supported:
            try:
                tender = parse_file(str(fpath))
                tenders.append(tender)
            except Exception as e:
                print(f"  [WARN] Could not parse {fpath.name}: {e}")
    print(f"  Loaded {len(tenders)} tenders from {tenders_dir}")
    return tenders


def load_profiles(profiles_path: str = "data/profiles.json") -> list:
    """Load business profiles."""
    with open(profiles_path, "r") as f:
        profiles = json.load(f)
    print(f"  Loaded {len(profiles)} profiles from {profiles_path}")
    return profiles


if __name__ == "__main__":
    tenders = load_tenders()
    for t in tenders[:3]:
        print(f"\n  {t['id']} | {t['sector']} | {t['language']} | budget={t['budget']} | deadline={t['deadline']}")
        print(f"  Title: {t['title'][:60]}")
