#!/usr/bin/env python3
"""
app.py — Streamlit UI for CPI Tender Matcher
Enhanced with:
  - Agentic resoning for intelligent match explanations
  - Custom profile input: manual form OR PDF upload
  - Existing pre-built profile selection preserved

Deploy on Streamlit Community Cloud: https://streamlit.io/cloud
Run locally:  streamlit run app.py
"""

import sys
import json
import time
import io
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.parser import load_tenders, load_profiles
from src.ranker import TenderRanker, get_top_disqualifier
from src.summarizer import generate_summary
from src.utils import get_profile_language, format_budget, ensure_dir

# ── Optional imports (graceful fallback if not installed) ──────────────────────
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# ─── Config ───────────────────────────────────────────────────────────────────
import os

def _load_groq_api_key() -> str:
    """Load GROQ_API_KEY from Streamlit secrets, then environment variable fallback."""
    # 1. Streamlit Cloud secrets (st.secrets)
    try:
        key = st.secrets["GROQ_API_KEY"]
        if key:
            return key
    except (KeyError, FileNotFoundError):
        pass
    # 2. Local environment variable (e.g. from a .env file loaded externally)
    key = os.environ.get("GROQ_API_KEY", "")
    return key

GROQ_API_KEY = _load_groq_api_key()
GROQ_MODEL   = "openai/gpt-oss-20b"
# Disable LLM features silently if the key was not found
GROQ_AVAILABLE = GROQ_AVAILABLE and bool(GROQ_API_KEY)

SECTORS = ["agritech", "healthtech", "cleantech", "edtech", "fintech", "wastetech", "general"]
REGIONS = ["East Africa", "West Africa", "Central Africa", "Southern Africa", "Africa"]

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CPI Tender Matcher",
    page_icon="🌍",
    layout="wide",
)

# ─── Load tender data once (cached) ───────────────────────────────────────────
@st.cache_resource
def load_data():
    tenders  = load_tenders("data/tenders")
    profiles = load_profiles("data/profiles.json")
    ranker   = TenderRanker(tenders)
    return tenders, profiles, ranker


TENDERS, PROFILES, RANKER = load_data()
PROFILE_MAP     = {p["id"]: p for p in PROFILES}
PROFILE_CHOICES = [f"{p['id']} — {p['name']} ({p['country']})" for p in PROFILES]


# ─── Groq LLM helper ──────────────────────────────────────────────────────────
def groq_explain_match(profile, tender, rank, score, breakdown, language="en"):
    """
    Use Groq (openai/gpt-oss-20b) to generate a rich, personalised match explanation.
    Falls back to the template-based summarizer if Groq is unavailable or fails.
    """
    if not GROQ_AVAILABLE:
        return generate_summary(profile, tender, rank, score, breakdown, language)

    lang_instruction = "Respond in French." if language == "fr" else "Respond in English."

    system_prompt = (
        "You are an expert grant advisor helping African cooperatives and startups "
        "find the best-matched tenders and grants. Your explanations are concise, "
        "actionable, and encouraging. Always respond in at most 100 words."
    )

    user_prompt = (
        f"Explain why this tender is a great (or partial) match for the organization below.\n"
        f"{lang_instruction}\n\n"
        f"## Organization Profile\n"
        f"- Name: {profile.get('name')}\n"
        f"- Sector: {profile.get('sector')}\n"
        f"- Country: {profile.get('country')}\n"
        f"- Employees: {profile.get('employees', 'N/A')}\n"
        f"- Needs: {profile.get('needs_text', '')}\n"
        f"- Budget capacity: USD {profile.get('budget_max', 0):,}\n\n"
        f"## Matched Tender (Rank #{rank})\n"
        f"- Title: {tender.get('title')}\n"
        f"- Sector: {tender.get('sector')}\n"
        f"- Budget: USD {tender.get('budget', 0):,}\n"
        f"- Deadline: {tender.get('deadline')}\n"
        f"- Region: {tender.get('region')}\n\n"
        f"## Scoring Breakdown\n"
        f"- Composite score: {score:.4f}/1.0\n"
        f"- TF-IDF similarity: {breakdown.get('tfidf_similarity', 0):.2%}\n"
        f"- Sector match: {breakdown.get('sector_match', 0):.2%}\n"
        f"- Budget fit: {breakdown.get('budget_score', 0):.2%}\n"
        f"- Deadline urgency: {breakdown.get('urgency_score', 0):.2%}\n\n"
        f"Write a compelling max-100-word explanation and suggest one next step."
    )

    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=180,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"Groq LLM unavailable ({e}); using template summary.")
        return generate_summary(profile, tender, rank, score, breakdown, language)


def groq_parse_pdf_profile(pdf_text):
    """
    Ask Groq to extract a structured profile from raw PDF text.
    Returns a dict matching the profiles.json schema.
    """
    if not GROQ_AVAILABLE:
        return {}

    system_prompt = (
        "You are a data extraction assistant. Extract organisation profile information "
        "from the text and return ONLY valid JSON — no markdown, no explanation."
    )

    user_prompt = (
        "Extract the following fields from the document text below and return a JSON object.\n"
        "If a field is not found, use a sensible default.\n\n"
        "Required JSON keys:\n"
        "  id          — use \"custom_pdf\"\n"
        "  name        — organisation name (string)\n"
        "  sector      — one of: agritech, healthtech, cleantech, edtech, fintech, wastetech, general\n"
        "  country     — country name (string)\n"
        "  employees   — number of employees (integer, default 0)\n"
        "  languages   — list of language codes, e.g. [\"en\"] or [\"fr\"]\n"
        "  needs_text  — 1-3 sentence description of what funding is needed for\n"
        "  past_funding — past funding received in USD (integer, default 0)\n"
        "  budget_max  — maximum grant amount sought in USD (integer, default 50000)\n"
        "  region      — one of: East Africa, West Africa, Central Africa, Southern Africa, Africa\n\n"
        f"Document text:\n\"\"\"\n{pdf_text[:4000]}\n\"\"\"\n\n"
        "Return ONLY the JSON object."
    )

    try:
        client   = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.strip("```json").strip("```").strip()
        return json.loads(raw)
    except Exception as e:
        st.error(f"Could not parse profile from PDF: {e}")
        return {}


def extract_pdf_text(uploaded_file):
    """Extract raw text from an uploaded PDF file."""
    if not PYPDF_AVAILABLE:
        return ""
    reader = pypdf.PdfReader(io.BytesIO(uploaded_file.read()))
    pages  = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🌍 CPI Tender Matcher")
st.markdown(
    "**Multilingual Grant Finder for African Cooperatives**  \n"
    "AIMS KTT Hackathon · T2.2 | Author: Samson Niyizurugero  \n"
    "Supports English 🇬🇧 and French 🇫🇷 · Powered by **Groq LLM** ⚡"
)
if GROQ_AVAILABLE:
    st.success(f"⚡ Groq LLM active — model: `{GROQ_MODEL}`")
else:
    st.warning("⚠️ `groq` package not installed. Run `pip install groq` to enable LLM explanations.")

st.divider()


# ─── Sidebar: Settings ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    language = st.selectbox(
        "Output Language",
        options=["EN", "FR"],
        help="Language for match explanations",
    )

    top_k = st.slider(
        "Top-K Results",
        min_value=1, max_value=10, value=5, step=1,
        help="Number of tenders to return",
    )

    use_llm = st.toggle(
        "Use Groq LLM Explanations",
        value=True,
        help="Use Groq AI for richer explanations (slower but smarter)",
    )

    st.divider()
    st.markdown("### 📖 How It Works")
    st.markdown(
        "1. **Profile** — Select an existing profile, fill in the form, or upload a PDF  \n"
        "2. **Parse** — Tenders parsed from TXT/HTML/PDF, language detected  \n"
        "3. **Rank** — Hybrid scoring: `0.45×TF-IDF + 0.25×Sector + 0.20×Budget + 0.10×Urgency`  \n"
        "4. **Explain** — Groq LLM generates personalised explanations  \n"
        "5. **Deploy** — Designed for rural cooperatives via WhatsApp/SMS/voice"
    )


# ─── Profile Input — Three Modes ──────────────────────────────────────────────
st.subheader("👤 Business Profile")

profile_mode = st.radio(
    "How would you like to provide your profile?",
    options=["📋 Select existing profile", "✏️ Fill in manually", "📄 Upload PDF"],
    horizontal=True,
)

profile = None

# ── Mode 1: Select existing ────────────────────────────────────────────────────
if profile_mode == "📋 Select existing profile":
    profile_choice = st.selectbox(
        "Select Business Profile",
        options=[""] + PROFILE_CHOICES,
        help="Choose a pre-loaded cooperative or business profile",
    )
    if profile_choice:
        profile_id = profile_choice.split("—")[0].strip()
        profile    = PROFILE_MAP.get(profile_id)
        if profile:
            with st.expander("👁️ Profile Details", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Name",      profile.get("name"))
                c2.metric("Sector",    profile.get("sector"))
                c3.metric("Country",   profile.get("country"))
                c4.metric("Employees", profile.get("employees", "—"))
                st.markdown(f"**Languages:** {', '.join(profile.get('languages', ['en'])).upper()}")
                st.markdown(f"**Needs:** {profile.get('needs_text', '')}")

# ── Mode 2: Manual form ────────────────────────────────────────────────────────
elif profile_mode == "✏️ Fill in manually":
    with st.form("manual_profile_form"):
        st.markdown("#### Enter your organisation details")

        col_a, col_b = st.columns(2)
        with col_a:
            m_name    = st.text_input("Organisation Name *", placeholder="e.g. AgriGrow Rwanda")
            m_country = st.text_input("Country *",           placeholder="e.g. Rwanda")
            m_sector  = st.selectbox("Sector *", SECTORS)
            m_region  = st.selectbox("Region *", REGIONS)
        with col_b:
            m_employees  = st.number_input("Number of Employees",         min_value=0, value=10)
            m_budget_max = st.number_input("Max Grant Sought (USD)",       min_value=0, value=50000, step=5000)
            m_past_fund  = st.number_input("Past Funding Received (USD)", min_value=0, value=0,     step=1000)
            m_lang       = st.multiselect("Languages", ["en", "fr"],      default=["en"])

        m_needs = st.text_area(
            "Describe your funding needs *",
            placeholder="e.g. We need funding to scale our precision farming app...",
            height=100,
        )
        submitted = st.form_submit_button("✅ Use This Profile", type="primary")

    if submitted:
        if not m_name or not m_country or not m_needs:
            st.error("Please fill in the required fields: Name, Country, and Needs.")
        else:
            profile = {
                "id":           "custom_manual",
                "name":         m_name,
                "sector":       m_sector,
                "country":      m_country,
                "employees":    int(m_employees),
                "languages":    m_lang or ["en"],
                "needs_text":   m_needs,
                "past_funding": int(m_past_fund),
                "budget_max":   int(m_budget_max),
                "region":       m_region,
            }
            st.session_state["manual_profile"] = profile
            st.success(f"✅ Profile set: **{m_name}** ({m_sector}, {m_country})")

    if "manual_profile" in st.session_state and profile is None:
        profile = st.session_state["manual_profile"]
        st.info(f"Using saved manual profile: **{profile['name']}**")

# ── Mode 3: PDF Upload ─────────────────────────────────────────────────────────
elif profile_mode == "📄 Upload PDF":
    if not PYPDF_AVAILABLE:
        st.error("`pypdf` is not installed. Run `pip install pypdf` to enable PDF upload.")
    elif not GROQ_AVAILABLE:
        st.error("`groq` is not installed. Run `pip install groq` to enable PDF profile extraction.")
    else:
        uploaded_pdf = st.file_uploader(
            "Upload your organisation profile as a PDF",
            type=["pdf"],
            help="The AI will extract your organisation details automatically",
        )
        if uploaded_pdf:
            if st.button("🤖 Extract Profile from PDF", type="primary"):
                with st.spinner("Groq AI is reading your PDF..."):
                    pdf_text = extract_pdf_text(uploaded_pdf)
                    if not pdf_text.strip():
                        st.error("Could not extract text from the PDF. Try a text-based PDF.")
                    else:
                        extracted = groq_parse_pdf_profile(pdf_text)
                        if extracted:
                            profile = extracted
                            st.session_state["pdf_profile"] = profile
                            st.success("✅ Profile extracted successfully!")
                            with st.expander("📋 Extracted Profile", expanded=True):
                                st.json(profile)
                        else:
                            st.error("Could not extract a profile. Try filling in the form manually.")

        if "pdf_profile" in st.session_state and profile is None:
            profile = st.session_state["pdf_profile"]
            st.info(f"Using PDF-extracted profile: **{profile.get('name', 'Unknown')}**")


st.divider()

# ─── Match Button ─────────────────────────────────────────────────────────────
match_btn = st.button("🔍 Find Matching Tenders", type="primary", use_container_width=True)


# ─── Main Results ─────────────────────────────────────────────────────────────
if match_btn:
    if not profile:
        st.warning("Please provide a business profile first (select, fill in, or upload).")
    else:
        lang = language.lower()

        with st.spinner("Matching tenders..."):
            t0      = time.time()
            matches = RANKER.rank(profile, top_k=int(top_k))
            elapsed = time.time() - t0

        label = profile.get("name", "Your Organisation")
        if lang == "fr":
            st.success(f"🏆 Top {top_k} Subventions pour **{label}** — Traité en {elapsed:.2f}s · {len(TENDERS)} appels analysés")
        else:
            st.success(f"🏆 Top {top_k} Tenders for **{label}** — Processed in {elapsed:.2f}s · {len(TENDERS)} tenders analysed")

        results_lines = []

        for rank_idx, match in enumerate(matches, 1):
            score      = match["score"]
            breakdown  = match["breakdown"]
            budget_str = format_budget(match.get("budget", 0))
            lang_badge = "🇫🇷 FR" if match["language"] == "fr" else "🇬🇧 EN"
            disq       = get_top_disqualifier(profile, match)

            if use_llm and GROQ_AVAILABLE:
                with st.spinner(f"⚡ Groq generating explanation for match #{rank_idx}..."):
                    summary = groq_explain_match(profile, match, rank_idx, score, breakdown, lang)
            else:
                summary = generate_summary(profile, match, rank_idx, score, breakdown, lang)

            with st.container():
                st.markdown(f"### #{rank_idx} — {match['title']}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Score",    f"{score:.4f}")
                m2.metric("Sector",   match["sector"])
                m3.metric("Budget",   budget_str)
                m4.metric("Language", lang_badge)
                st.markdown(
                    f"**ID:** `{match['tender_id']}` | "
                    f"**Deadline:** {match['deadline']} | "
                    f"**Region:** {match['region']}"
                )
                st.info(summary)

                with st.expander("📊 Score Breakdown"):
                    b1, b2, b3, b4 = st.columns(4)
                    b1.metric("🔍 TF-IDF",  f"{breakdown['tfidf_similarity']:.3f}")
                    b2.metric("🏷 Sector",  f"{breakdown['sector_match']:.3f}")
                    b3.metric("💰 Budget",  f"{breakdown['budget_score']:.3f}")
                    b4.metric("⏰ Urgency", f"{breakdown['urgency_score']:.3f}")
                    st.warning(f"⚠ Biggest Disqualifier: {disq}")

                st.divider()
                results_lines.append(f"### #{rank_idx} — {match['title']}")
                results_lines.append(f"**Score:** {score:.4f} | **Sector:** {match['sector']} | **Budget:** {budget_str} | {lang_badge}")
                results_lines.append(f"**Deadline:** {match['deadline']} | **Region:** {match['region']}")
                results_lines.append(f"\n> {summary}\n")
                results_lines.append(f"**Biggest Disqualifier:** {disq}\n---")

        results_md = "\n".join(results_lines)

        ensure_dir("summaries")
        profile_id   = profile.get("id", "custom")
        summary_path = f"summaries/profile_{profile_id}_{lang}.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(results_md)

        scores_data = {
            "profile_id":      profile_id,
            "profile_name":    profile.get("name"),
            "language":        lang,
            "llm_used":        use_llm and GROQ_AVAILABLE,
            "elapsed_seconds": round(elapsed, 3),
            "matches": [
                {
                    "rank":      i + 1,
                    "tender_id": m["tender_id"],
                    "title":     m["title"],
                    "score":     m["score"],
                    "breakdown": m["breakdown"],
                }
                for i, m in enumerate(matches)
            ],
        }
        scores_json = json.dumps(scores_data, indent=2)

        plain_summary = f"Results for {profile.get('name', 'your organisation')}. "
        for i, m in enumerate(matches, 1):
            plain_summary += f"Number {i}: {m['title']}, score {m['score']:.2f}. "

        st.subheader("📥 Export Results")
        tab1, tab2, tab3 = st.tabs(["📄 Markdown Preview", "📊 JSON Scores", "🔊 Plain Text (Audio/WhatsApp)"])

        with tab1:
            st.download_button(
                "⬇ Download Markdown",
                data=results_md,
                file_name=f"matches_{profile_id}_{lang}.md",
                mime="text/markdown",
            )
            st.divider()
            # Build a richer markdown document and render it properly
            header_md = (
                f"## 🌍 Tender Match Report\n"
                f"**Organisation:** {profile.get('name', '—')} &nbsp;|&nbsp; "
                f"**Sector:** {profile.get('sector', '—')} &nbsp;|&nbsp; "
                f"**Country:** {profile.get('country', '—')}\n\n"
                f"**Language:** {lang.upper()} &nbsp;|&nbsp; "
                f"**LLM Explanations:** {'✅ Yes' if use_llm and GROQ_AVAILABLE else '❌ No'} &nbsp;|&nbsp; "
                f"**Processing time:** {elapsed:.2f}s\n\n"
                f"---\n"
            )
            st.markdown(header_md)

            for rank_idx, match in enumerate(matches, 1):
                score      = match["score"]
                breakdown  = match["breakdown"]
                budget_str = format_budget(match.get("budget", 0))
                lang_badge = "🇫🇷 FR" if match["language"] == "fr" else "🇬🇧 EN"
                disq       = get_top_disqualifier(profile, match)

                # Retrieve already-generated summary from results_lines
                summary_text = ""
                for line in results_lines:
                    if line.startswith(f"> ") and results_lines.index(line) > 0:
                        prev = results_lines[results_lines.index(line) - 2]
                        if f"#{rank_idx} —" in prev:
                            summary_text = line[2:].strip()
                            break

                score_pct = int(score * 100)
                bar_filled = "█" * (score_pct // 5)
                bar_empty  = "░" * (20 - score_pct // 5)

                match_md = (
                    f"### #{rank_idx} — {match['title']}\n\n"
                    f"| Field | Value |\n"
                    f"|---|---|\n"
                    f"| 🏷 Sector | `{match['sector']}` |\n"
                    f"| 💰 Budget | {budget_str} |\n"
                    f"| 📅 Deadline | {match['deadline']} |\n"
                    f"| 🌍 Region | {match['region']} |\n"
                    f"| 🗣 Language | {lang_badge} |\n"
                    f"| 🎯 Score | **{score:.4f}** — `{bar_filled}{bar_empty}` |\n\n"
                    f"**Score Breakdown:** "
                    f"TF-IDF `{breakdown['tfidf_similarity']:.3f}` · "
                    f"Sector `{breakdown['sector_match']:.3f}` · "
                    f"Budget `{breakdown['budget_score']:.3f}` · "
                    f"Urgency `{breakdown['urgency_score']:.3f}`\n\n"
                    f"> ⚠️ **Biggest disqualifier:** {disq}\n\n"
                )
                st.markdown(match_md)
                if summary_text:
                    st.info(summary_text)
                st.divider()

        with tab2:
            st.download_button(
                "⬇ Download JSON",
                data=scores_json,
                file_name=f"scores_{profile_id}_{lang}.json",
                mime="application/json",
            )
            st.code(scores_json, language="json")

        with tab3:
            st.text_area(
                "Audio-friendly summary (copy for WhatsApp/SMS)",
                plain_summary,
                height=120,
            )
