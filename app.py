#!/usr/bin/env python3
"""
app.py — Streamlit UI for CPI Tender Matcher
Deploy on Streamlit Community Cloud (free): https://streamlit.io/cloud

Run locally:
  streamlit run app.py
"""

import sys
import json
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import load_tenders, load_profiles
from src.ranker import TenderRanker, get_top_disqualifier
from src.summarizer import generate_summary
from src.utils import get_profile_language, format_budget, ensure_dir


# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CPI Tender Matcher",
    page_icon="🌍",
    layout="wide",
)


# ─── Load data once at startup (cached) ───────────────────────────────────────
@st.cache_resource
def load_data():
    tenders = load_tenders("data/tenders")
    profiles = load_profiles("data/profiles.json")
    ranker = TenderRanker(tenders)
    return tenders, profiles, ranker


TENDERS, PROFILES, RANKER = load_data()
PROFILE_MAP = {p["id"]: p for p in PROFILES}
PROFILE_CHOICES = [f"{p['id']} — {p['name']} ({p['country']})" for p in PROFILES]


# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🌍 CPI Tender Matcher")
st.markdown(
    "**Multilingual Grant Finder for African Cooperatives**  \n"
    "AIMS KTT Hackathon · T2.2 | Author: Samson Niyizurugero  \n"
    "Supports English 🇬🇧 and French 🇫🇷 · CPU-only · < 3 minutes for 10 profiles."
)
st.divider()

# ─── Sidebar: Settings ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    profile_choice = st.selectbox(
        "Select Business Profile",
        options=[""] + PROFILE_CHOICES,
        help="Choose your cooperative or business profile",
    )

    language = st.selectbox(
        "Output Language",
        options=["EN", "FR"],
        help="Language for match explanations",
    )

    top_k = st.slider(
        "Top-K Results",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
        help="Number of tenders to return",
    )

    match_btn = st.button("🔍 Find Matching Tenders", type="primary", use_container_width=True)

    st.divider()
    st.markdown("### 📖 How It Works")
    st.markdown(
        "1. **Parse** — Tenders are parsed from TXT/HTML/PDF, language detected, fields extracted  \n"
        "2. **Rank** — Hybrid scoring: `0.45×TF-IDF + 0.25×Sector + 0.20×Budget + 0.10×Urgency`  \n"
        "3. **Explain** — ≤80-word summaries generated in your chosen language  \n"
        "4. **Deploy** — Designed for rural cooperatives via WhatsApp/SMS/voice agents"
    )


# ─── Profile Info ─────────────────────────────────────────────────────────────
if profile_choice:
    profile_id = profile_choice.split("—")[0].strip()
    profile = PROFILE_MAP.get(profile_id)
    if profile:
        with st.expander("👤 Profile Details", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Name", profile.get("name"))
            col2.metric("Sector", profile.get("sector"))
            col3.metric("Country", profile.get("country"))
            col4.metric("Employees", profile.get("employees", "—"))
            st.markdown(f"**Languages:** {', '.join(profile.get('languages', ['en'])).upper()}")
            st.markdown(f"**Needs:** {profile.get('needs_text', '')}")


# ─── Main Results ─────────────────────────────────────────────────────────────
if match_btn:
    if not profile_choice:
        st.warning("Please select a profile first.")
    else:
        profile_id = profile_choice.split("—")[0].strip()
        profile = PROFILE_MAP.get(profile_id)

        if not profile:
            st.error(f"Profile '{profile_id}' not found.")
        else:
            lang = language.lower() if language in ["EN", "FR"] else get_profile_language(profile)

            with st.spinner("Matching tenders..."):
                t0 = time.time()
                matches = RANKER.rank(profile, top_k=int(top_k))
                elapsed = time.time() - t0

            if lang == "fr":
                st.success(f"🏆 Top {top_k} Subventions pour **{profile['name']}** — Traité en {elapsed:.2f}s · {len(TENDERS)} appels analysés")
            else:
                st.success(f"🏆 Top {top_k} Tenders for **{profile['name']}** — Processed in {elapsed:.2f}s · {len(TENDERS)} tenders analysed")

            # ── Render each match ──────────────────────────────────────────────
            results_lines = []

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

                with st.container():
                    st.markdown(f"### #{rank_idx} — {match['title']}")

                    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                    meta_col1.metric("Score", f"{score:.4f}")
                    meta_col2.metric("Sector", match["sector"])
                    meta_col3.metric("Budget", budget_str)
                    meta_col4.metric("Language", lang_badge)

                    st.markdown(f"**ID:** `{match['tender_id']}` | **Deadline:** {match['deadline']} | **Region:** {match['region']}")
                    st.info(summary)

                    with st.expander("📊 Score Breakdown"):
                        b1, b2, b3, b4 = st.columns(4)
                        b1.metric("🔍 TF-IDF", f"{breakdown['tfidf_similarity']:.3f}")
                        b2.metric("🏷 Sector", f"{breakdown['sector_match']:.3f}")
                        b3.metric("💰 Budget", f"{breakdown['budget_score']:.3f}")
                        b4.metric("⏰ Urgency", f"{breakdown['urgency_score']:.3f}")
                        st.warning(f"⚠ Biggest Disqualifier: {disq}")

                    st.divider()

                    # Accumulate for markdown export
                    results_lines.append(f"### #{rank_idx} — {match['title']}")
                    results_lines.append(f"**Score:** {score:.4f} | **Sector:** {match['sector']} | **Budget:** {budget_str} | {lang_badge}")
                    results_lines.append(f"**Deadline:** {match['deadline']} | **Region:** {match['region']}")
                    results_lines.append(f"\n> {summary}\n")
                    results_lines.append(f"**Biggest Disqualifier:** {disq}\n---")

            results_md = "\n".join(results_lines)

            # Save summary file
            ensure_dir("summaries")
            summary_path = f"summaries/profile_{profile_id}_{lang}.md"
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(results_md)

            # ── JSON Scores ────────────────────────────────────────────────────
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
                ],
            }
            scores_json = json.dumps(scores_data, indent=2)

            # ── Plain text summary ─────────────────────────────────────────────
            plain_summary = f"Results for {profile['name']}. "
            for i, m in enumerate(matches, 1):
                plain_summary += f"Number {i}: {m['title']}, score {m['score']:.2f}. "

            # ── Download / export tabs ─────────────────────────────────────────
            st.subheader("📥 Export Results")
            tab1, tab2, tab3 = st.tabs(["📄 Markdown", "📊 JSON Scores", "🔊 Plain Text (Audio/WhatsApp)"])

            with tab1:
                st.download_button(
                    "⬇ Download Markdown",
                    data=results_md,
                    file_name=f"matches_{profile_id}_{lang}.md",
                    mime="text/markdown",
                )
                st.code(results_md, language="markdown")

            with tab2:
                st.download_button(
                    "⬇ Download JSON",
                    data=scores_json,
                    file_name=f"scores_{profile_id}_{lang}.json",
                    mime="application/json",
                )
                st.code(scores_json, language="json")

            with tab3:
                st.text_area("Audio-friendly summary (copy for WhatsApp/SMS)", plain_summary, height=120)
