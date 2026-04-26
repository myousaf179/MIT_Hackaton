# UNMAPPED — Backend & Data Pipeline

> **Closing the distance between real skills and economic opportunity in the age of AI.**
>
> Built for the World Bank Youth Summit × Hack-Nation Global AI Hackathon 2026.
>
> The frontend ships separately (Lovable). This repository is the data + API layer.

---

## What this is

UNMAPPED is **infrastructure, not just an app** (per the brief's page 3). Think
protocol, not product. Country-specific parameters — labor market data, education
taxonomy, language, automation calibration — are **inputs to the system, not
hardcoded assumptions**.

Concretely, this backend:

1. Crawls **real, citable** data from World Bank WDI, ILO ILOSTAT, the
   Wittgenstein Centre and ESCO.
2. Maps free-text informal skills (Amara's "I fix phones") to a portable
   ESCO/ISCO profile with full provenance.
3. Calculates **LMIC-calibrated** automation risk on top of Frey-Osborne (2017),
   showing every factor in the response so the user can interrogate it.
4. Surfaces **≥3 econometric signals** per request with explicit `source_url`
   fields — never buried in the algorithm.
5. Issues a **portable JSON-LD OpenBadges-v2 credential** the user can carry
   across borders and sectors.
6. Exposes a **dual interface**: youth view (`POST /analyze`) and policymaker
   view (`GET /policymaker/{iso3}`).
7. Optionally augments the static crawled signals with **live, current,
   country-specific opportunities and news** via the
   [Tavily](https://app.tavily.com/) Search API — see
   [Live opportunities & news (Tavily)](#live-opportunities--news-tavily).

Every numeric value the API returns carries `{value, unit, year, source_name,
source_url, indicator_code, crawled_at}` — no synthetic proxies.

---

## Quick start

```bash
cd unmapped-backend
python -m pip install -r requirements.txt
cp .env.example .env

# Pre-crawl real data for the demo countries (GHA + BGD)
python -m scripts.seed_demo

# Run the API
uvicorn api.app:app --reload --port 8000
```

Then visit `http://localhost:8000/docs` for the OpenAPI explorer.

### Try the Amara scenario

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I fix phones and learned a bit of python from YouTube",
    "country_code": "GHA",
    "is_rural": false
  }'
```

You will get back: 2 ESCO-mapped skills (phone repair → ISCO 7421, write
computer code → ISCO 2512), a calibrated risk number with factor breakdown,
≥3 econometric signals each with a `source_url`, a Wittgenstein 2020-2035
education trajectory, an opportunities panel, and a JSON-LD credential.

---

## Adding a new country in 5 minutes

The brief explicitly demands country-agnostic configurability. Here is the
demonstration:

1. Copy [`config/countries/_template.yaml`](config/countries/_template.yaml)
   to `config/countries/<ISO3>.yaml` (e.g. `NGA.yaml`).
2. Fill in `iso3`, `iso2`, `name`, `languages`, `currency`, `default_rural_share`,
   `itu_digital_penetration`, plus the lists of `sectors_of_interest`,
   `ilostat_indicators`, `worldbank_indicators`, and `wittgenstein_years`.
3. Run `python -m scripts.crawl <ISO3>`.
4. Restart the API. The new country appears at `GET /countries`.

**Zero code changes required.** The crawlers, matcher, risk calculator and
econometric layer all read country parameters from the YAML.

---

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `/health` | Liveness probe |
| GET  | `/` | Service metadata + list of available countries |
| GET  | `/countries` | All configured countries with `has_processed_data` flag |
| GET  | `/skills/search?q=<text>` | Skill autocomplete (used by frontend) |
| GET  | `/signals/{iso3}/{sector}` | Single-sector signal lookup |
| POST | `/analyze` | Module 1 + 2 + 3 youth-facing analysis |
| GET  | `/policymaker/{iso3}` | Aggregate dashboard view (Module 3 dual interface) |

Full schemas at `/docs`.

### `POST /analyze` request body

```json
{
  "text": "free-text description of skills",
  "country_code": "GHA",
  "is_rural": false,
  "language": "en"
}
```

### `POST /analyze` response shape

```json
{
  "country_code": "GHA",
  "country_name": "Ghana",
  "language": "en",
  "profile": { "skills": [...], "isco_codes": [...], "sectors": [...], "human_readable_summary": [...] },
  "risk_assessment": {
    "overall_risk": 0.25,
    "overall_risk_percentage": 25.0,
    "base_risk_percentage": 40.4,
    "band": "low",
    "factors": {
      "frey_osborne_base": { "value": 0.404, "explanation": "..." },
      "digital_factor":    { "value": 0.728, "explanation": "..." },
      "rurality_factor":   { "value": 0.85,  "explanation": "..." }
    },
    "durable_skills": ["..."],
    "calibration_disclaimer": "..."
  },
  "econometric_signals": [
    { "value": 215.0, "unit": "USD per month", "source_url": "https://ilostat.ilo.org/...", ... },
    { "value": 12.6,  "unit": "%",             "source_url": "https://data.worldbank.org/...", ... },
    ...
  ],
  "education_trajectory": { "label": "...", "points": [{"year": 2020, "value": 46.1, "source_url": "..."}, ...] },
  "opportunities": {
    "adjacent_skills": [...],
    "sector_anchors": [...],
    "training_pathways": [...],
    "live_opportunities": [
      { "title": "...", "url": "https://...", "snippet": "...", "published_date": "2026-03-01", "source_name": "Tavily", "matched_for": {"sector": "TELECOM", "skill": "..."} }
    ],
    "live_source": "tavily"
  },
  "portable_credential": { "@context": "https://w3id.org/openbadges/v2", "type": "Assertion", ... }
}
```

`opportunities.live_source` is `"tavily"` when live results are present and
`"static-fallback"` when Tavily is disabled or returned nothing — the panel
always renders.

---

## Architecture

```
unmapped-backend/
├── config/                  # Country YAMLs — the localizability layer
│   ├── countries/
│   │   ├── _template.yaml
│   │   ├── GHA.yaml
│   │   └── BGD.yaml
│   ├── sectors.yaml         # Shared ISIC Rev.4 / ILOSTAT classif1 mapping
│   ├── settings.py          # Pydantic-settings (env-driven)
│   └── country_loader.py
├── crawlers/
│   ├── base.py              # Retries (tenacity), file cache, provenance envelope
│   ├── worldbank.py         # api.worldbank.org/v2 — JSON, no auth
│   ├── ilostat.py           # rplumber.ilo.org bulk CSV endpoint
│   ├── wittgenstein.py      # GitHub mirror of WCDE v2 CSVs + fallback projections
│   ├── esco.py              # ec.europa.eu/esco/api — used to enrich the taxonomy
│   ├── frey_osborne.py      # Loads bundled CSV, maps SOC → ISCO-08
│   ├── tavily.py            # api.tavily.com — live opportunities + policymaker news
│   └── orchestrator.py      # crawl_country(iso3) → data/processed/<iso3>.json
├── data/
│   ├── reference/           # Bundled in repo:
│   │   ├── frey_osborne_2017.csv
│   │   ├── soc_to_isco08.csv
│   │   └── isco08_titles.csv
│   ├── processed/
│   │   ├── skills_taxonomy.json   # Hand-curated seed (12 skills covering brief archetypes)
│   │   ├── gha.json                # Created by `scripts.crawl GHA`
│   │   └── bgd.json
│   ├── raw/                 # gitignored — TTL cache for crawled responses
│   └── sources.json         # Auto-generated provenance registry (every URL we hit)
├── matching/
│   ├── skill_matcher.py     # Hybrid: keyword (substring) + RapidFuzz token_set_ratio
│   ├── risk_calculator.py   # base × digital_factor × rurality_factor
│   ├── econometric.py       # ≥3 signals + education trajectory + policymaker view
│   └── opportunities.py     # Adjacency-driven, grounded opportunity surfacing
├── api/
│   ├── app.py               # FastAPI app + lifespan
│   ├── deps.py              # Cached SkillMatcher singleton
│   ├── schemas.py           # Pydantic v2 request/response models
│   └── routes/
│       ├── analyze.py
│       ├── countries.py
│       ├── skills.py
│       ├── signals.py
│       └── policymaker.py
├── core/
│   ├── cache.py             # File-based TTL cache (hashed keys)
│   ├── logging.py           # structlog setup
│   └── credential.py        # OpenBadges v2 / JSON-LD assertion builder
├── scripts/
│   ├── crawl.py             # python -m scripts.crawl GHA BGD
│   ├── build_taxonomy.py    # python -m scripts.build_taxonomy --validate / --expand
│   └── seed_demo.py         # Pre-crawl every configured country
├── tests/                   # pytest — 27 tests, all green (incl. mocked Tavily)
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

### Data flow

```
                      ┌──────────────────────────┐
                      │  Lovable frontend (UI)   │
                      └───────────┬──────────────┘
                                  │ HTTP
                      ┌───────────▼──────────────┐
                      │      FastAPI app         │
                      └─────┬──────┬──────┬──────┘
                            │      │      │
                ┌───────────▼─┐ ┌──▼───┐ ┌▼──────────────┐
                │ SkillMatcher│ │ Risk │ │ Econometric / │
                │  (hybrid)   │ │ calc │ │ Policymaker   │
                └──────┬──────┘ └──┬───┘ └──────┬────────┘
                       │           │            │
                       │           │            │
              ┌────────▼─┐    ┌────▼───┐  ┌─────▼─────┐
              │ taxonomy │    │ Frey-  │  │ data/     │
              │ JSON     │    │ Osborne│  │ processed │
              └──────────┘    └────────┘  └─────▲─────┘
                                                │ written by
                                                │
                              ┌─────────────────┴─────────┐
                              │  scripts/crawl.py (CLI)   │
                              └────┬──────┬───────┬───────┘
                                   │      │       │
                          ┌────────▼┐  ┌──▼───┐ ┌─▼─────────────┐
                          │ World   │  │ ILO  │ │ Wittgenstein  │
                          │  Bank   │  │STAT  │ │   Centre      │
                          └─────────┘  └──────┘ └───────────────┘
```

---

## Live opportunities & news (Tavily)

The brief calls for **reachable** opportunities — not generic links. To get
there we use [Tavily](https://app.tavily.com/) Search to retrieve current,
country-specific results at request time. Two integration points:

| Endpoint | What Tavily adds | Field in response |
| --- | --- | --- |
| `POST /analyze` | Live training programs, apprenticeships and reachable jobs scoped to the user's matched skills + country | `opportunities.live_opportunities` (≤ 8 items) |
| `GET /policymaker/{iso3}` | Recent labour-market / automation / training news (last 180 days) for the country | `recent_signals` (≤ 5 items) |

Each Tavily result carries `{title, url, snippet, score, published_date,
source_name: "Tavily", fetched_at}` — same provenance contract as the static
signals. The `live_source` (or `recent_signals_source`) field tells the
frontend whether the panel is live or fell back to the offline path.

### Setup

```bash
# In .env — get a key at https://app.tavily.com
UNMAPPED_ENABLE_TAVILY=true
UNMAPPED_TAVILY_API_KEY=tvly-...
UNMAPPED_TAVILY_MAX_RESULTS=5
UNMAPPED_TAVILY_NEWS_DAYS=180
```

### Behaviour & cost control

- **Offline-safe.** If `UNMAPPED_TAVILY_API_KEY` is empty, `is_enabled()`
  returns `False`, the live calls are skipped, and the static
  `_TRAINING_HINTS` path drives `opportunities.training_pathways`. **The demo
  keeps working with no API key** — useful for offline judges.
- **Cached.** Every search is cached via the existing `FileCache` keyed by
  `tavily:{topic}:{days}:{max_results}:{normalised_query}`. TTL is the same
  `UNMAPPED_CACHE_TTL_HOURS` value used by the other crawlers (default 24h),
  so repeating the same `/analyze` request inside a day costs zero credits.
- **Bounded fanout.** `/analyze` runs at most 4 Tavily searches per request
  (one per top skill/sector pair), and clips the merged result list to 8.
- **Soft-fail.** Network errors or HTTP non-200 responses log a warning and
  return `[]` — the rest of the response is unaffected.

### Disable per-deployment

```bash
UNMAPPED_ENABLE_TAVILY=false
```

This is the right setting for offline demos, smoke tests, or when you are
out of credits.

---

## Risk model (transparent on purpose)

```
base_risk        = mean( frey_osborne_probability(isco) for isco in user_skills )
digital_factor   = 1 - itu_digital_penetration * digital_weight
rurality_factor  = rural_factor if is_rural else urban_factor
overall_risk     = base_risk * digital_factor * rurality_factor
```

Every factor is returned in the response with a plain-language explanation. The
brief's page 2 demands the profile is "explainable to a non-expert user" — this
is how we deliver it.

A skill is **durable** if its individual calibrated risk falls below 0.35; the
response lists durable and vulnerable skills separately.

---

## Provenance contract

Every numeric value carried by the API conforms to:

```json
{
  "value": 12.6,
  "unit": "%",
  "year": "2023",
  "source_name": "World Bank WDI",
  "source_url": "https://data.worldbank.org/indicator/SL.UEM.1524.ZS?locations=GH",
  "indicator_code": "SL.UEM.1524.ZS",
  "crawled_at": "2026-04-26T10:30:00Z",
  "note": "Youth unemployment."
}
```

This makes it trivial for the frontend to render a "Source" link beside any
number — directly addressing the brief's "Surface at least 2 econometric
signals visibly to the user — not buried in the algorithm" requirement.

---

## Modules ↔ brief mapping

| Brief module | What this backend ships |
| --- | --- |
| **01 Skills Signal Engine** | Hybrid `SkillMatcher` (keyword + fuzzy) maps free-text to ESCO labels with ISCO-08 codes. `human_readable_summary` field is plain-English. JSON-LD credential is portable across borders and sectors. |
| **02 AI Readiness & Displacement Risk Lens** | LMIC-calibrated risk built on Frey-Osborne (2017). Wittgenstein 2020-2035 SSP2 trajectory included. Calibration is configurable per country YAML. |
| **03 Opportunity Matching & Econometric Dashboard** | ≥3 surfaced econometric signals on every analyse call. Adjacency-driven opportunity surfacing **plus live, country-specific opportunities and news strip via Tavily** (graceful offline fallback). **Dual interface**: `POST /analyze` for youth, `GET /policymaker/{iso3}` for aggregate dashboards. |

---

## Localizability checklist (brief, page 3)

| Configurable item | Where it lives | Reconfigure for a new context? |
| --- | --- | --- |
| Labor market data source / structure | `country.ilostat_indicators`, `country.worldbank_indicators`, `config/sectors.yaml` | YAML |
| Education taxonomy & credential mapping | `data/processed/skills_taxonomy.json` | JSON (regenerate via ESCO) |
| Language / script of UI | `country.languages` (frontend reads it) | YAML |
| Automation exposure calibration | `country.itu_digital_penetration`, `country.automation_calibration` | YAML |
| Opportunity types surfaced (offline) | `matching/opportunities._TRAINING_HINTS` (sector-keyed) | One Python dict |
| Opportunity types surfaced (live) | Tavily search query template in `matching/opportunities._opportunity_queries` | Adjust the query string |

---

## Honest limits

The brief explicitly rewards "be honest about limits." Here's what we know we don't know:

- **Frey-Osborne is US-centric.** The LMIC calibration applied here is a
  documented heuristic (digital penetration × rurality factor), not a
  validated econometric model. Treat figures as directional, not predictive.
- **ILOSTAT coverage is uneven.** When a country/sector pair is missing from
  the bulk download we fall back to a regional ILO average and label the data
  point with `note: "Approximated from regional average"` so the frontend can
  show a warning badge.
- **ESCO is EU-centric and English-first.** For Bangla / Twi we surface the
  English ESCO label alongside the locale's display name. Full localisation
  of skill labels is a future enhancement.
- **Initial taxonomy ships ~12 skills** covering the brief's archetypes (phone
  repair, retail, agriculture, software, web, driving, teaching, nursing,
  sewing, construction, cooking, bookkeeping). Run
  `python -m scripts.build_taxonomy --expand "<query>"` to enrich it from the
  live ESCO API.
- **The credential is unsigned.** We emit a stable JSON-LD OpenBadges-v2
  shape; downstream verifiers can re-issue with a real key when this becomes
  production infrastructure.

---

## Development

```bash
# Run the test suite (no network calls — uses a pre-built fixture bundle)
python -m pytest -q

# Validate the taxonomy
python -m scripts.build_taxonomy --validate

# Expand the taxonomy from live ESCO
python -m scripts.build_taxonomy --expand "data analysis" "graphic design"

# Enable the optional embedding fallback
echo UNMAPPED_ENABLE_EMBEDDINGS=true >> .env
python -m pip install sentence-transformers   # 90 MB model download
```

---

## License

MIT.
