# Spotify AI-Powered Review Discovery Engine

## Quickstart

```bash
cd spotify-discovery-engine
pip install -r requirements.txt
streamlit run app/main.py
```

## Architecture

```
spotify-discovery-engine/
├── src/
│   ├── scrapers/          # Reddit (3-strategy fallback), Forum, YouTube API
│   ├── pipeline/          # Noise filtering + behavioral enrichment
│   └── analyzer/          # LLM prompt templates + PM report generation
├── app/main.py            # Streamlit dashboard (5 views)
├── data/raw/              # Mock data (5 sources, 100+ reviews)
└── data/processed/        # Auto-generated on first run
```

## Five Dashboard Views

1. **Executive Dashboard** — KPIs, ingestion funnel, gauges, Premium vs Free analysis
2. **Data Sources Explorer** — Sortable/searchable table per source with AI tags
3. **Strategic PM Insights** — Discovery Q&A, recommendations, verbatim quotes
4. **Semantic Query Playground** — Natural language search over all reviews
5. **AI Workflow** — Pipeline blueprint, noise filtering logic, tagging taxonomy
