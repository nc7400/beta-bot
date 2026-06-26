# 🧗 Beta-Bot — Mountain Project Q&A

A local Streamlit chatbot that answers questions about your personal climbing history using your Mountain Project CSV export. Answers are grounded strictly in your data — the bot will never invent a route name, grade, date, or style.

---

## Features

- Upload your Mountain Project CSV and ask natural-language questions
- Accurate counts and lists for any grade, area, style, or date range
- Correct hardest/easiest lookups using Mountain Project's numeric difficulty codes — per discipline, never cross-compared
- Powered by Groq's free API tier (no credit card required)
- Stays well under Groq's token limits via per-question context filtering

---

## Requirements

- Python 3.10+
- A free [Groq API key](https://console.groq.com) — sign up with Google or GitHub, no credit card needed

Install dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
streamlit>=1.35.0
groq>=1.0.0
```

---

## Quick Start

```bash
streamlit run app.py
```

Then in the sidebar:

1. Paste your Groq API key (`gsk_...`)
2. Upload your Mountain Project CSV export
3. Click **Load & Process Data**
4. Click **Initialize Bot**
5. Ask anything about your climbs

---

## Exporting Your Data from Mountain Project

1. Log in at [mountainproject.com](https://www.mountainproject.com)
2. Go to your profile → **Ticks**
3. Click **Export CSV**

The exported file works directly — no preprocessing needed.

---

## Example Questions

```
List all my 5.12d climbs
How many 5.13a routes have I done?
What is my hardest redpoint?
List all my onsights at Muir Valley
Which area have I visited the most?
How many climbs did I log in 2025?
What boulder problems have I sent?
What's my easiest sport climb?
```

---

## Project Structure

```
├── app.py          # Streamlit UI and Groq API calls
├── ingest.py       # Data processing, statistics, and context generation
├── fetch.py        # CSV/JSON loading and field normalisation
├── requirements.txt
└── data/
    └── uploads/    # Temporary storage for uploaded files
```

---

## How It Works

### 1. Data Loading (`fetch.py`)

Reads your Mountain Project CSV and normalises every row into a consistent record with these fields:

| Field | Source Column |
|---|---|
| `route_name` | Route |
| `grade` | Grade |
| `area` | Extracted from Location breadcrumb |
| `full_location` | Location (full breadcrumb) |
| `date` | Date |
| `your_rating` | Your Rating |
| `avg_stars` | Average Rating |
| `type` | Route Type |
| `style` | Style |
| `lead_style` | Lead Style |
| `notes` | Notes |
| `length` | Length In Feet |
| `pitches` | Pitches |
| `your_grade` | Your Suggested Grade |
| `rating_code` | Rating Code (integer) |

### 2. Processing and Statistics (`ingest.py`)

Builds aggregate statistics including:

- Total climbs, unique routes, unique areas
- Grade distribution and area visit counts
- Lead style breakdown (Redpoint / Onsight / Flash / Send)
- Hardest and easiest climb **per discipline** using `rating_code`

### 3. Per-Question Context Filtering

Every question gets its own filtered context — only the relevant records are sent to the model. This keeps requests under Groq's 12,000 token-per-minute free-tier limit regardless of how large your tick list is.

**Routing logic:**

| Question type | Records sent | Typical tokens |
|---|---|---|
| Grade-specific (`5.12d`, `V7`) | All matching rows, no cap | ~500–800 |
| Route name or area lookup | All matching rows, no cap | ~400–900 |
| Global (`hardest`, `total`, `areas`) | Stats block + 80 most recent rows | ~2,500 |
| No question (init) | Stats block only | ~400 |

The stats block is always included so the model can answer aggregate questions without needing every raw row.

### 4. LLM Context Format

Each matching record is sent in labeled `key=value` format to eliminate column ambiguity:

```
date=2026-06-02 | route=Wicked Games | grade=5.12d | difficulty_code=7500 | area=Graining Fork Nature Preserve | lead_style=Redpoint | type=Sport | your_rating=4.0
```

Fields are only included if populated — `your_suggested_grade` is omitted entirely when empty, preventing star-rating values from appearing in a grade-shaped column.

### 5. LLM Backend (`app.py`)

Uses the **Groq API** with a two-model waterfall:

| Model | Role |
|---|---|
| `llama-3.3-70b-versatile` | Primary — best instruction-following quality |
| `llama-3.1-8b-instant` | Fallback — higher rate limits, used if primary hits 413 |

`temperature=0` is set on all requests for deterministic, non-creative responses.

Modules are force-reloaded from disk on each data load using `importlib.reload()` to prevent Streamlit's module cache from serving stale code after updates.

---

## The Rating Code

Mountain Project's `Rating Code` column is a numeric difficulty index. It is **only valid within the same discipline** — the scales are completely separate:

| Discipline | Rating Code Range | Examples |
|---|---|---|
| Sport / Trad | Low thousands | 5.7 = 1800 · 5.12a = 6600 · 5.13c = 9200 |
| Boulder | 20000s | V4 = 20400 · V7 = 20700 · V8 = 20800 |

A V1 (~20100) is **not** harder than a 5.13a (8600). The bot enforces this: hardest/easiest lookups are always answered per discipline, and cross-discipline comparisons are explicitly forbidden in the grounding rules sent to the model.

---

## Anti-Hallucination Design

Every layer of the system is designed to prevent the model from inventing information:

**Context layer:**
- Full raw records (not summaries) are sent for matching queries
- Records use labeled `key=value` format — no positional ambiguity
- `your_suggested_grade` is omitted when empty (prevents star ratings from appearing in a grade-shaped position)
- Grade-specific queries always scan the full dataset — no record cap

**Prompt layer:**
- Hard rules forbid inventing any route name, grade, date, area, or style
- `COUNT = number of records listed` — the model is told not to estimate
- `LIST = copy records verbatim` — no rephrasing or verification loops
- Mid-answer revision is explicitly forbidden (`"never loop, revise mid-answer, or say 'however' about your own output"`)
- Discipline boundary for `difficulty_code` is stated in grounding rules

**Model layer:**
- `temperature=0` eliminates creative/probabilistic output
- If the answer is not in the data, the model returns a fixed phrase: `"I do not have that information in the data provided."`

---

## Troubleshooting

**413 token limit error**

This means the context is still too large for Groq's free tier. The app will automatically retry with the fallback model (`llama-3.1-8b-instant`). If both fail, try asking a more specific question — include a grade, route name, or area to trigger targeted filtering.

**Bot returns stale answers after a code change**

Click **Load & Process Data** again in the sidebar. This triggers `importlib.reload()` on `fetch.py` and `ingest.py`, forcing the updated code to load from disk.

**Wrong route count**

Ensure you clicked **Load & Process Data** after uploading your file. If counts still seem off, check your CSV for duplicate entries — Mountain Project sometimes exports the same tick twice if you've logged a route more than once.

**Groq API key not accepted**

Keys start with `gsk_`. Generate one at [console.groq.com](https://console.groq.com) → API Keys → Create API Key.

---

## Known Limitations

- Global questions (e.g. "list every climb I've ever done") cap at 80 most-recent records to stay under token limits. More specific questions (by grade, area, or route name) have no cap.
- Routes with split grades in the CSV (e.g. `5.12a/b`, `5.12+`) are treated as their own grade category and won't match a query for `5.12a` or `5.12b` individually.
- Boulder and sport difficulty codes cannot be meaningfully compared.