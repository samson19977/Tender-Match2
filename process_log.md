# Process Log — CPI Tender Matcher
## AIMS KTT Hackathon · T2.2 · Multilingual Grant & Tender Matcher
**Author:** Samson Niyizurugero  
**Date:** 2025-04-23  
**Total Time:** ~3.5 hours

---

## ⏱ Hour-by-Hour Timeline

| Time | Activity |
|------|----------|
| 0:00–0:30 | Read brief carefully. Identified 5 core deliverables: parser, ranker, summarizer, Gradio UI, village_agent.md. Sketched architecture on paper. |
| 0:30–1:00 | Built `generate_data.py` — synthetic tender generator producing 40 docs in EN/FR across 6 sectors and 4 budget tiers. Tested output, verified language distribution (60/40). |
| 1:00–1:45 | Built `src/parser.py` — rule-based field extraction (budget regex, deadline regex, language detection, sector keywords). Tested on 5 sample tenders manually. |
| 1:45–2:15 | Built `src/ranker.py` — TF-IDF vectorizer + hybrid scoring. Defined formula: `0.45×tfidf + 0.25×sector + 0.20×budget + 0.10×urgency`. Justified weights with judge-explainability in mind. |
| 2:15–2:30 | Built `src/summarizer.py` — template-based summary generator in EN and FR. Ensured ≤80-word output. Added FR word choices for cooperative context. |
| 2:30–2:45 | Built `matcher.py` CLI — full pipeline orchestration. Added `--profile`, `--all`, `--eval` flags. Tested: `python matcher.py --profile 02 --topk 5`. |
| 2:45–3:15 | Built `app.py` — Gradio UI with profile dropdown, language selector, top-k slider, markdown output, JSON scores panel, plain-text audio summary. |
| 3:15–3:30 | Wrote `village_agent.md` — cost analysis for 3 delivery models with RWF math. Wrote privacy/consent plan. |
| 3:30–3:45 | Wrote `README.md`, `SIGNED.md`, `process_log.md`. Created evaluation notebook skeleton. |
| 3:45–4:00 | Final review: tested pipeline end-to-end, checked all files present, verified GitHub structure. |

---

## 🤖 LLM & Tool Usage Declaration

| Tool | How Used |
|------|----------|
| **Claude (Anthropic)** | Architecture planning, code scaffolding, debugging, documentation writing |
| **GitHub Copilot** | Inline autocompletion during coding |
| No other tools used | — |

**What I added beyond the LLM:** Local context about cooperative financing in Rwanda, RWF cost estimates from real-world experience, word choice decisions in French summaries (e.g., "coopérative" vs "organisation"), debugging the TF-IDF index for multilingual corpus, and the urgency scoring function design.

---

## 📝 Three Sample Prompts Sent to Claude

### Prompt 1 (Used):
> *"Design a hybrid scoring function for tender-profile matching that combines TF-IDF cosine similarity, sector match, budget compatibility, and deadline urgency. Make it explainable for non-technical judges. Show the formula and justify each weight."*

**Why:** I needed a scoring function that was both performant and easy to explain in a 4-minute demo. Claude suggested the 0.45/0.25/0.20/0.10 split which I kept after validating against sample profiles.

### Prompt 2 (Used):
> *"Write a village_agent.md for rural Uganda deployment of a tender matching system. Include cost analysis for 3 options: voice call center, WhatsApp audio broadcast, printed bulletin. Give RWF math for 500 cooperatives."*

**Why:** The product/business section is worth 20% of the score. I used Claude to structure the comparison table, then manually adjusted costs based on real Rwandan mobile data prices I know from experience.

### Prompt 3 (Discarded):
> *"Use sentence-transformers paraphrase-multilingual-MiniLM-L12-v2 for embeddings in the ranker instead of TF-IDF."*

**Why discarded:** After checking, the model is ~470MB — exceeding the 150MB constraint. I switched to TF-IDF with `sklearn` which is fast, CPU-only, and fully explainable. This was the right call for the constraint.

---

## 🧩 Hardest Decision

**The hardest decision was choosing between embedding-based similarity and TF-IDF.**

The brief mentions paraphrase-multilingual-MiniLM as an option, which would give better cross-lingual retrieval (matching a French tender to an English profile). However, the MiniLM model at ~470MB violates the 150MB constraint. 

I chose TF-IDF with `ngram_range=(1,2)` and `sublinear_tf=True` for three reasons:
1. It stays within the size constraint (no model file — vectorizer is built at runtime)
2. It runs in <1 second for 40 documents even on CPU
3. The formula is 100% explainable to judges — I can show the term weights live

The trade-off is weaker cross-lingual matching. I mitigated this by including language detection in the pipeline and boosting sector keywords during query construction.
