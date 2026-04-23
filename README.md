# 🌍 CPI Tender Matcher
### Multilingual Grant & Tender Matcher for African Cooperatives
**AIMS KTT Hackathon · T2.2** | Author: Samson Niyizurugero

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://YOUR_APP_NAME.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue)](https://python.org)
[![CPU Only](https://img.shields.io/badge/CPU-Only-orange)](requirements.txt)

---

## 📌 What It Does

Matches African cooperative business profiles to the most relevant grants and tenders from a corpus of 40+ multilingual documents (EN/FR). Generates ≤80-word plain-language explanations in the profile's language.

**Scoring Formula:**
```
score = 0.45 × TF-IDF_similarity
      + 0.25 × sector_match
      + 0.20 × budget_compatibility
      + 0.10 × deadline_urgency
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   CPI TENDER MATCHER                     │
│                                                          │
│  INPUT                                                   │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │ Tender Docs  │    │  Business    │                   │
│  │ (.txt/.html/ │    │  Profile     │                   │
│  │  .pdf)  40x  │    │ (profiles.   │                   │
│  └──────┬───────┘    │  json) 10x   │                   │
│         │            └──────┬───────┘                   │
│         ▼                   ▼                            │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │   PARSER     │    │  QUERY       │                   │
│  │ - Lang detect│    │  BUILDER     │                   │
│  │ - Field extract    - needs_text │                    │
│  │ - Budget/date│    │ + sector×3  │                    │
│  │ - pypdf (PDF)│    └──────┬───────┘                   │
│  └──────┬───────┘           │                            │
│         │                   │                            │
│         ▼                   ▼                            │
│  ┌─────────────────────────────────┐                    │
│  │         TF-IDF RANKER            │                    │
│  │   sklearn TfidfVectorizer        │                    │
│  │   ngram=(1,2) max_features=5000  │                    │
│  │   + sector_match_score()         │                    │
│  │   + budget_compatibility_score() │                    │
│  │   + deadline_urgency_score()     │                    │
│  └──────────────┬──────────────────┘                    │
│                  │ Top-5 matches                         │
│                  ▼                                       │
│  ┌──────────────────────────────────┐                   │
│  │        SUMMARIZER                 │                   │
│  │  Template-based EN/FR generation  │                   │
│  │  ≤ 80 words · Cooperative-voice   │                   │
│  └──────────────┬───────────────────┘                   │
│                  │                                       │
│  OUTPUT          ▼                                       │
│  ┌──────────────────────────────────┐                   │
│  │  Ranked tenders + scores         │                   │
│  │  Summaries (.md per match pair)  │                   │
│  │  Streamlit UI (GitHub hosted)    │                   │
│  │  Village Agent (WhatsApp/Voice)  │                   │
│  └──────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (2 Commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate data and run matcher
python generate_data.py && python matcher.py --profile 02 --topk 5
```

---

## 📦 Full Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/cpi-tender-matcher
cd cpi-tender-matcher

# Install
pip install -r requirements.txt

# Generate synthetic data (40 tenders + profiles + gold matches)
python generate_data.py

# Run matcher for a single profile
python matcher.py --profile 02 --topk 5

# Run all profiles with evaluation
python matcher.py --all --eval --topk 5

# Launch Streamlit UI locally
streamlit run app.py
```

---

## 🎮 Demo Commands

```bash
# Profile 02 (SantéPlus Senegal — FR)
python matcher.py --profile 02 --topk 5 --lang fr

# Profile 07 (AgriCoopérative Kinshasa — FR)
python matcher.py --profile 07 --topk 5 --lang fr

# Profile 03 (CleanEnergy Kenya — EN)
python matcher.py --profile 03 --topk 5 --lang en

# All profiles with evaluation
python matcher.py --all --eval
```

---

## 📁 Project Structure

```
cpi-tender-matcher/
│
├── README.md              ← This file
├── matcher.py             ← Full pipeline CLI
├── app.py                 ← Streamlit UI
├── generate_data.py       ← Synthetic data generator
├── requirements.txt       ← Dependencies
├── process_log.md         ← Development log + LLM disclosure
├── SIGNED.md              ← Honor code signature
├── village_agent.md       ← Rural deployment strategy
│
├── data/
│   ├── tenders/           ← 40 tender documents (.txt)
│   ├── profiles.json      ← 10 business profiles
│   ├── tenders_meta.json  ← Tender metadata index
│   └── gold_matches.csv   ← Expert ground truth (3 per profile)
│
├── summaries/             ← Generated match explanations (.md)
│   ├── profile_01_en.md   ← Per-profile overview
│   ├── profile_01_T029_en.md  ← Per-(profile, tender) pair
│   └── ...                ← 60 files total (10 overview + 50 pair)
│
├── notebooks/
│   └── evaluation.ipynb   ← MRR@5, Recall@5, error analysis (executed)
│
└── src/
    ├── parser.py          ← Document parsing (.txt/.html/.pdf via pypdf)
    ├── ranker.py          ← Hybrid TF-IDF ranking engine
    ├── summarizer.py      ← EN/FR explanation generator
    └── utils.py           ← Shared utilities + metrics
```

---

## 📊 Evaluation Results

| Metric | Value |
|--------|-------|
| **MRR@5** | **0.6833** |
| **Recall@5** | **0.7667** |

Run: `python matcher.py --all --eval`

See `notebooks/evaluation.ipynb` for the full per-profile breakdown and confusion case analysis.

---

## 🌿 Rural Deployment

See [`village_agent.md`](village_agent.md) for the full offline deployment strategy:
- WhatsApp Audio Broadcast (recommended)
- Cost: **1,115 RWF/cooperative/month** (~$0.86)
- Supports 2G/feature phones
- Multilingual TTS (Kinyarwanda, Wolof, Lingala)

---

## 🎥 Demo Video

[📺 Watch 4-minute demo →](YOUR_VIDEO_URL_HERE)

---

## ⚙️ Technical Constraints Met

| Constraint | Status |
|------------|--------|
| CPU-only | ✅ sklearn TF-IDF, no GPU |
| Model < 150MB | ✅ No model file (vectorizer built at runtime) |
| < 3 min for 10 profiles | ✅ ~8 seconds total |
| PDF parsing | ✅ pypdf with pdftotext fallback |
| Reproducible in ≤ 2 commands | ✅ See Quick Start |
| EN + FR support | ✅ Language detection + FR summaries |

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
