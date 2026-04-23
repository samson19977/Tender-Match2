# 🌿 Village Agent — Rural Deployment Strategy
## CPI Tender Matcher · AIMS KTT Hackathon T2.2
**Author:** Samson Niyizurugero

---

## 🎯 Target User

An **illiterate cooperative leader** in rural Rwanda, DRC, or Senegal who:
- Has a feature phone (not a smartphone)
- Speaks Kinyarwanda, Lingala, or Wolof primarily
- Has intermittent or no internet access
- Leads a 15–50 person farming or artisan cooperative
- Cannot read bureaucratic grant documents in EN or FR

---

## 📡 Chosen Distribution Model: WhatsApp Audio Broadcast

After comparing all three options (see cost analysis below), **WhatsApp Audio Broadcast** is recommended as the primary channel, with a **Village Agent** as the last-mile human interface.

---

## 📅 Weekly Cadence

| Day | Action | Actor |
|-----|--------|-------|
| **Monday** | System runs matcher for all 200 cooperative profiles | Automated server |
| **Monday** | Top 3 matches per cooperative → 60-second audio clip generated (TTS in local language) | Automated |
| **Tuesday** | Audio clips sent via WhatsApp Business API to district village agents | System |
| **Wednesday** | Village agent listens, simplifies message, calls cooperative leader | Village Agent |
| **Thursday** | Cooperative leader decides to apply → agent assists with form | Village Agent |
| **Friday** | Application submitted or flagged for next week | Village Agent |

---

## 📞 Weekly Message Script (EN Template)

> *"Hello [Name]. I am calling from the CPI Grant Finder. This week, we found 3 grants that match your cooperative in [sector]. The best match is the [Grant Name] from [Org Name]. It offers up to USD [amount] for [sector] in [region]. The deadline is [date]. Your cooperative qualifies because [1-line reason]. To apply, you need [2 documents]. Should I send you the application link by SMS?"*

**French version (Exemple):**

> *"Bonjour [Nom]. Je vous appelle du Service CPI de Subventions. Cette semaine, nous avons trouvé 3 subventions correspondant à votre coopérative. La meilleure est [Nom Subvention] de [Org], jusqu'à USD [montant] pour [secteur]. Date limite : [date]. Pour postuler, vous avez besoin de [2 documents]. Voulez-vous que je vous envoie le lien par SMS ?"*

---

## 💰 Cost Analysis — All Three Options

### Option A: Voice Call Center → IVR → Human Agent

| Item | Unit Cost | Monthly (200 coops) |
|------|-----------|---------------------|
| IVR system setup | $500 one-time | — |
| Per-call cost (3 min avg) | $0.08/min | $96 |
| Agent salary (2 agents) | $300/agent | $600 |
| Phone/data bundle | $30/agent | $60 |
| **Total/month** | | **$756** |
| **CAC per cooperative** | | **$3.78/month** |

---

### Option B: WhatsApp Audio Broadcast ✅ RECOMMENDED

| Item | Unit Cost | Monthly (200 coops) |
|------|-----------|---------------------|
| WhatsApp Business API | $0.005/message | $1 |
| TTS audio generation (local) | Free (offline TTS) | $0 |
| 1 Village Agent (part-time) | $150/month | $150 |
| Mobile data bundle | $20 | $20 |
| **Total/month** | | **$171** |
| **CAC per cooperative** | | **$0.86/month** |

**At 500 cooperatives (RWF math):**
- $171/month × 500/200 = $427.50/month
- At 1 USD = 1,300 RWF → **555,750 RWF/month**
- Per cooperative: **1,115 RWF/month** (~$0.86)

---

### Option C: Printed Bulletin Board at District Cooperative

| Item | Unit Cost | Monthly (200 coops) |
|------|-----------|---------------------|
| Printing (2 pages × 200) | $0.10/page | $40 |
| Distribution agent | $200 | $200 |
| Paper/supplies | $20 | $20 |
| **Total/month** | | **$260** |
| **CAC per cooperative** | | **$1.30/month** |

*Limitation: Not timely (weekly print cycle), no interaction possible, low engagement rate.*

---

## ✅ Recommendation: WhatsApp Audio Broadcast

**Why WhatsApp wins:**
1. **Lowest CAC** — $0.86/cooperative/month vs $3.78 (voice center) vs $1.30 (print)
2. **Async delivery** — agent listens when available, no missed calls
3. **Multilingual** — TTS in Kinyarwanda, Wolof, Lingala at zero extra cost
4. **Scalable** — adding 300 more cooperatives adds only $60/month
5. **High penetration** — WhatsApp used by >60% of feature phone users in Rwanda/Senegal

---

## 🔒 Privacy & Consent Plan

- Cooperative leaders explicitly opt-in via SMS keyword: **"JOIN CPI"**
- Data stored: cooperative name, sector, phone number, preferred language only
- No individual financial data collected
- Opt-out: reply "STOP" at any time
- Data hosted on local server in Rwanda (compliance with Rwanda Data Protection Law 2021)
- No tender application data shared with third parties
- Village agents sign a simple 1-page data confidentiality agreement

---

## 🌱 Scale-Up Path

| Phase | Cooperatives | Monthly Cost | CAC |
|-------|-------------|--------------|-----|
| Pilot (Month 1–3) | 50 | $60 | $1.20 |
| Growth (Month 4–6) | 200 | $171 | $0.86 |
| Scale (Month 7–12) | 500 | $428 | $0.86 |
| National (Year 2) | 2,000 | $1,200 | $0.60 |

*CAC drops as fixed costs are spread over more cooperatives.*

---

## 🔧 Technical Notes for Offline/Low-Bandwidth

- Tender matching runs server-side (no device requirement)
- Audio clips compressed to 64kbps MP3 (~480KB per 60-second clip)
- Clips delivered via WhatsApp (auto-compresses to ~200KB)
- Fallback: SMS text summary (160 chars) for feature phones without WhatsApp
- Village agent app works fully offline — syncs when WiFi available
- System designed for 2G/3G connectivity (tested on 64kbps uplink)
