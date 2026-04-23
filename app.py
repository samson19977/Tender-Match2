#!/usr/bin/env python3
"""
app.py — Gradio UI for CPI Tender Matcher
Deploy on Hugging Face Spaces: https://huggingface.co/spaces

Run locally:
  python app.py
"""

import os
import sys
import json
import time
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import load_tenders, load_profiles
from src.ranker import TenderRanker, get_top_disqualifier
from src.summarizer import generate_summary
from src.utils import get_profile_language, format_budget, ensure_dir


# ─── Load data once at startup ────────────────────────────────────────────────
print("🔄 Loading tenders and profiles...")
TENDERS = load_tenders("data/tenders")
PROFILES = load_profiles("data/profiles.json")
RANKER = TenderRanker(TENDERS)
PROFILE_MAP = {p["id"]: p for p in PROFILES}
PROFILE_CHOICES = [f"{p['id']} — {p['name']} ({p['country']})" for p in PROFILES]
print("✅ System ready!")


# ─── Core Function ────────────────────────────────────────────────────────────

def match_tenders(profile_choice: str, language: str, top_k: int) -> tuple:
    """
    Main matching function called by Gradio.
    Returns: (results_markdown, scores_json, summary_text)
    """
    if not profile_choice:
        return "Please select a profile.", "{}", ""

    # Parse profile ID
    profile_id = profile_choice.split("—")[0].strip()
    profile = PROFILE_MAP.get(profile_id)
    if not profile:
        return f"Profile '{profile_id}' not found.", "{}", ""

    lang = language.lower() if language in ["EN", "FR"] else get_profile_language(profile)

    # Run matching
    t0 = time.time()
    matches = RANKER.rank(profile, top_k=int(top_k))
    elapsed = time.time() - t0

    # Build results markdown
    lines = []
    if lang == "fr":
        lines.append(f"## 🏆 Top {top_k} Subventions pour {profile['name']}")
        lines.append(f"*Traité en {elapsed:.2f}s · {len(TENDERS)} appels analysés*\n")
    else:
        lines.append(f"## 🏆 Top {top_k} Tenders for {profile['name']}")
        lines.append(f"*Processed in {elapsed:.2f}s · {len(TENDERS)} tenders analysed*\n")

    for rank_idx, match in enumerate(matches, 1):
        score = match["score"]
        breakdown = match["breakdown"]
        budget_str = format_budget(match.get("budget", 0))
        lang_badge = "🇫🇷 FR" if match["language"] == "fr" else "🇬🇧 EN"
        disq = get_top_disqualifier(profile, match)

        summary = generate_summary(
            profile=profile,
            tender=match,
            rank=rank_idx,
            score=score,
            breakdown=breakdown,
            language=lang,
        )

        lines.append(f"### #{rank_idx} — {match['title']}")
        lines.append(f"**ID:** `{match['tender_id']}` | **Score:** `{score:.4f}` | **Sector:** {match['sector']} | **Budget:** {budget_str} | {lang_badge}")
        lines.append(f"**Deadline:** {match['deadline']} | **Region:** {match['region']}")
        lines.append(f"\n> {summary}\n")
        lines.append(f"**Score Breakdown:**")
        lines.append(f"- 🔍 TF-IDF Similarity: `{breakdown['tfidf_similarity']:.3f}`")
        lines.append(f"- 🏷 Sector Match: `{breakdown['sector_match']:.3f}`")
        lines.append(f"- 💰 Budget Compatibility: `{breakdown['budget_score']:.3f}`")
        lines.append(f"- ⏰ Deadline Urgency: `{breakdown['urgency_score']:.3f}`")
        lines.append(f"\n⚠ **Biggest Disqualifier:** {disq}\n")
        lines.append("---")

    results_md = "\n".join(lines)

    # Save summary file
    ensure_dir("summaries")
    summary_path = f"summaries/profile_{profile_id}_{lang}.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(results_md)

    # JSON scores
    scores_data = {
        "profile_id": profile_id,
        "profile_name": profile["name"],
        "language": lang,
        "elapsed_seconds": round(elapsed, 3),
        "matches": [
            {
                "rank": i + 1,
                "tender_id": m["tender_id"],
                "title": m["title"],
                "score": m["score"],
                "breakdown": m["breakdown"],
            }
            for i, m in enumerate(matches)
        ]
    }
    scores_json = json.dumps(scores_data, indent=2)

    # Plain summary for audio (simplified)
    plain_summary = f"Results for {profile['name']}. "
    for i, m in enumerate(matches, 1):
        plain_summary += f"Number {i}: {m['title']}, score {m['score']:.2f}. "

    return results_md, scores_json, plain_summary


# ─── Profile Info Helper ──────────────────────────────────────────────────────

def show_profile_info(profile_choice: str) -> str:
    if not profile_choice:
        return ""
    profile_id = profile_choice.split("—")[0].strip()
    profile = PROFILE_MAP.get(profile_id)
    if not profile:
        return ""
    return (
        f"**Name:** {profile.get('name')} | **Sector:** {profile.get('sector')} | "
        f"**Country:** {profile.get('country')} | **Employees:** {profile.get('employees')} | "
        f"**Languages:** {', '.join(profile.get('languages', ['en'])).upper()}\n\n"
        f"**Needs:** {profile.get('needs_text', '')}"
    )


# ─── Gradio UI ────────────────────────────────────────────────────────────────

DESCRIPTION = """
# 🌍 CPI Tender Matcher — Multilingual Grant Finder for African Cooperatives

**AIMS KTT Hackathon · T2.2** | Author: Samson Niyizurugero

Match your business profile to the most relevant grants and tenders across Africa.  
Supports English 🇬🇧 and French 🇫🇷 · CPU-only · < 3 minutes for 10 profiles.

---
"""

with gr.Blocks(theme=gr.themes.Soft(), title="CPI Tender Matcher") as demo:
    gr.Markdown(DESCRIPTION)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Settings")
            profile_dd = gr.Dropdown(
                choices=PROFILE_CHOICES,
                label="Select Business Profile",
                info="Choose your cooperative or business profile"
            )
            profile_info = gr.Markdown(label="Profile Details")
            language_dd = gr.Dropdown(
                choices=["EN", "FR"],
                value="EN",
                label="Output Language",
                info="Language for match explanations"
            )
            topk_slider = gr.Slider(
                minimum=1, maximum=10, value=5, step=1,
                label="Top-K Results",
                info="Number of tenders to return"
            )
            match_btn = gr.Button("🔍 Find Matching Tenders", variant="primary", size="lg")

        with gr.Column(scale=2):
            gr.Markdown("### 📋 Results")
            results_md = gr.Markdown(label="Ranked Tenders")

    with gr.Accordion("📊 Raw JSON Scores", open=False):
        scores_json = gr.Code(language="json", label="Score Data")

    with gr.Accordion("🔊 Plain Text Summary (for Audio/WhatsApp)", open=False):
        plain_txt = gr.Textbox(label="Audio-friendly summary", lines=4)

    # Events
    profile_dd.change(fn=show_profile_info, inputs=profile_dd, outputs=profile_info)
    match_btn.click(
        fn=match_tenders,
        inputs=[profile_dd, language_dd, topk_slider],
        outputs=[results_md, scores_json, plain_txt]
    )

    gr.Markdown("""
---
### 📖 How It Works
1. **Parse** — Tenders are parsed from TXT/HTML/PDF, language detected, fields extracted  
2. **Rank** — Hybrid scoring: `0.45×TF-IDF + 0.25×Sector + 0.20×Budget + 0.10×Urgency`  
3. **Explain** — ≤80-word summaries generated in your chosen language  
4. **Deploy** — Designed for rural cooperatives via WhatsApp/SMS/voice agents
""")

if __name__ == "__main__":
    demo.launch(share=False)
