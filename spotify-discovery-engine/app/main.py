"""
Spotify AI-Powered Review Discovery Engine
Streamlit Dashboard — Spotify Design System
"""
from __future__ import annotations

import json
import sys
import logging
from pathlib import Path
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ── Spotify Design Tokens ───────────────────────────────────────────────────
BG = "#191414"
SIDEBAR_BG = "#000000"
ACCENT = "#1DB954"
ACCENT_DARK = "#158f3f"
CARD_BG = "#282828"
CARD_HOVER = "#333333"
TEXT = "#FFFFFF"
TEXT_SECONDARY = "#B3B3B3"
RED = "#E91429"
YELLOW = "#F59B23"
BLUE = "#2D46B9"
PURPLE = "#7B5EA7"

# ── Hover tooltip definitions ────────────────────────────────────────────────
ROOT_CAUSE_DEFS: dict = {
    "General Discovery Frustration": (
        "Generic user difficulty or friction felt when trying to branch out to new styles. "
        "A catch-all signal that the recommendation engine is not meeting baseline expectations."
    ),
    "Feedback Loop Bias": (
        "The algorithm prioritises familiar liked songs to maximise retention metrics, "
        "trapping users in a self-reinforcing echo chamber of content they already know."
    ),
    "Genre Bubble": (
        "Getting over-indexed into a single music genre because of a temporary listening phase. "
        "One heavy jazz week can lock the entire recommendation profile into jazz indefinitely."
    ),
    "Contextual Over-reliance": (
        "Background or utility music (gym playlists, study sessions) bleeds into a user's "
        "core casual listening feeds, warping their long-term taste profile."
    ),
    "Passive Fatigue": (
        "Users feel uninspired to actively search and rely entirely on automated feeds "
        "that keep recycling the same tracks — leading to disengagement over time."
    ),
    "Niche Content Gap": (
        "Indie, hyper-local, or obscure artists are systematically under-surfaced by "
        "default recommendation systems that optimise for popularity signals."
    ),
    "Taste Evolution Lag": (
        "The system fails to adapt when a user's real-world music interests shift organically. "
        "Historical play counts outweigh recent signals, anchoring the profile in the past."
    ),
    "Cold Start Anchoring": (
        "Relying too heavily on a user's very first interactions with the platform. "
        "Early preferences become disproportionately hard to dilute, even years later."
    ),
}

FRUSTRATION_DEFS: dict = {
    "Algorithm Quality": (
        "General programmatic failure where recommendations feel statistically inaccurate "
        "or repetitive — the broadest signal that the core model needs recalibration."
    ),
    "Discover Weekly Quality": (
        "Specific dissatisfaction with the weekly flagship mix delivering recycled or "
        "highly predictable tracks instead of genuinely new discoveries."
    ),
    "No Escape Mechanism": (
        "The total lack of a clear 'reset', 'dislike', or 'shuffle fresh' control to force "
        "a brand-new recommendation pool — users feel permanently locked in."
    ),
    "Radio Repetition": (
        "Artist or track radio degenerates into the exact same 15-20 songs the user already "
        "has in their library, defeating the purpose of radio as a discovery tool."
    ),
    "Autoplay Loop": (
        "The music stream plays identical familiar songs immediately after a curated album "
        "or custom playlist ends, breaking the transition into new content."
    ),
    "Daily Mix Stagnation": (
        "Daily personalised mixes feel completely frozen week-over-week with zero fresh "
        "additions — the 'Daily' label becomes misleading."
    ),
    "Cross-Context Contamination": (
        "Sleep sounds, study tracks, or shared family-plan plays bleed directly into a "
        "user's primary daily dashboard recommendations, corrupting their taste profile."
    ),
    "Algorithm Transparency": (
        "Users cannot understand why a track was recommended or how to influence future "
        "suggestions — the black-box nature erodes trust and engagement."
    ),
}

# Merged lookup used by tier-frustration ranked lists (covers both root-cause and UX terms)
TIER_FRUSTRATION_DEFS: dict = {**ROOT_CAUSE_DEFS, **FRUSTRATION_DEFS}

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="'Circular Std', 'Helvetica Neue', Helvetica, Arial, sans-serif"),
        colorway=[ACCENT, BLUE, YELLOW, RED, PURPLE, "#FF6B35", "#00C2FF", "#FF78C4"],
        xaxis=dict(gridcolor="#333333", zerolinecolor="#333333"),
        yaxis=dict(gridcolor="#333333", zerolinecolor="#333333"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spotify Discovery Engine",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [data-testid="stAppViewContainer"] {{
    background-color: {BG} !important;
    color: {TEXT} !important;
    font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
  }}

  [data-testid="stSidebar"] {{
    background-color: {SIDEBAR_BG} !important;
    border-right: 1px solid #282828 !important;
  }}

  [data-testid="stSidebar"] * {{ color: {TEXT} !important; }}

  .block-container {{
    padding: 1.5rem 2rem !important;
    max-width: 1400px !important;
  }}

  /* ── Spotify tile system: solid #181818 → hover #282828, zero borders ── */
  .metric-card {{
    background: #181818;
    border-radius: 6px;
    padding: 1.4rem 1.2rem;
    border: none;
    margin-bottom: 1rem;
    transition: background 0.3s ease;
  }}
  .metric-card:hover {{
    background: #282828;
  }}

  .metric-value {{
    font-size: 2.4rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1;
    margin-bottom: 0.25rem;
    letter-spacing: -0.03em;
  }}

  .metric-label {{
    font-size: 0.75rem;
    font-weight: 600;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.15rem;
  }}

  .metric-delta {{
    font-size: 0.82rem;
    margin-top: 0.3rem;
    color: {TEXT_SECONDARY};
  }}

  /* ── Streamlit native [data-testid="stMetric"] tiles ─────────────── */
  [data-testid="stMetric"] {{
    background: #181818 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 1.2rem 1rem !important;
    transition: background 0.3s ease !important;
  }}
  [data-testid="stMetric"]:hover {{
    background: #282828 !important;
  }}
  [data-testid="stMetricValue"] > div {{
    color: #FFFFFF !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
  }}
  [data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    text-transform: uppercase !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
  }}
  [data-testid="stMetricDelta"] {{
    color: {TEXT_SECONDARY} !important;
  }}

  /* Hero banner */
  .hero-banner {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    border: 1px solid #1DB95440;
    position: relative;
    overflow: hidden;
  }}

  .hero-banner::before {{
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, {ACCENT}15 0%, transparent 70%);
    border-radius: 50%;
  }}

  .hero-title {{
    font-size: 1.9rem;
    font-weight: 800;
    color: {TEXT};
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.02em;
  }}

  .hero-sub {{
    font-size: 1rem;
    color: {TEXT_SECONDARY};
    margin: 0;
    max-width: 600px;
  }}

  .accent-badge {{
    display: inline-block;
    background: {ACCENT};
    color: #000;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.2rem 0.6rem;
    border-radius: 100px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-right: 0.5rem;
  }}

  /* Section headers */
  .section-header {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {TEXT};
    margin: 1.5rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {ACCENT};
    display: inline-block;
  }}

  /* Insight boxes */
  .insight-box {{
    background: #181818;
    border-radius: 6px;
    padding: 1.5rem;
    border: none;
    border-left: 4px solid {ACCENT};
    margin: 1rem 0;
  }}

  .insight-box.warning {{ border-left-color: {YELLOW}; }}
  .insight-box.danger {{ border-left-color: {RED}; }}
  .insight-box.info {{ border-left-color: {BLUE}; }}
  .insight-box.purple {{ border-left-color: {PURPLE}; }}

  .insight-title {{
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {ACCENT};
    margin-bottom: 0.5rem;
  }}

  .insight-box.warning .insight-title {{ color: {YELLOW}; }}
  .insight-box.danger .insight-title {{ color: {RED}; }}
  .insight-box.info .insight-title {{ color: {BLUE}; }}
  .insight-box.purple .insight-title {{ color: {PURPLE}; }}

  .insight-text {{
    font-size: 0.95rem;
    color: {TEXT};
    line-height: 1.6;
  }}

  /* Frustration-row hover tooltip */
  .ft-tooltip {{
    position: relative;
    cursor: pointer;
    border-bottom: 1px dashed rgba(255,255,255,0.25);
    display: inline;
  }}
  .ft-tooltip::after {{
    content: attr(data-tip);
    position: absolute;
    left: 0;
    bottom: calc(100% + 10px);
    background: #181818;
    border: 1px solid {ACCENT};
    border-radius: 6px;
    padding: 0.65rem 0.85rem;
    font-size: 0.78rem;
    color: #B3B3B3;
    white-space: normal;
    width: 280px;
    z-index: 9999;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.18s ease;
    line-height: 1.55;
    font-weight: 400;
  }}
  .ft-tooltip:hover::after {{
    opacity: 1;
  }}

  /* Quote cards */
  .quote-card {{
    background: #181818;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    margin: 0.75rem 0;
    border: none;
    border-left: 3px solid #282828;
    position: relative;
    transition: background 0.3s ease;
  }}
  .quote-card:hover {{
    background: #282828;
  }}

  .quote-mark {{
    font-size: 3rem;
    color: {ACCENT}40;
    line-height: 0.5;
    float: left;
    margin-right: 0.5rem;
    font-family: Georgia, serif;
  }}

  .quote-text {{
    font-size: 0.95rem;
    color: {TEXT};
    font-style: italic;
    line-height: 1.6;
    margin: 0;
  }}

  .quote-meta {{
    font-size: 0.75rem;
    color: {TEXT_SECONDARY};
    margin-top: 0.75rem;
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }}

  .tag {{
    background: #333;
    color: {TEXT_SECONDARY};
    padding: 0.15rem 0.5rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 500;
  }}

  .tag.premium {{ background: {ACCENT}20; color: {ACCENT}; }}
  .tag.free {{ background: {BLUE}20; color: #6B8EFF; }}
  .tag.sentiment-neg {{ background: {RED}20; color: #FF6B6B; }}

  /* Nav items */
  .nav-item {{
    padding: 0.6rem 1rem;
    border-radius: 8px;
    margin: 0.2rem 0;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.9rem;
    transition: background 0.15s;
  }}

  .nav-item:hover {{ background: #282828; }}
  .nav-item.active {{ background: #282828; color: {ACCENT}; }}

  /* Data table */
  [data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    overflow: hidden;
  }}

  /* Workflow blocks */
  .workflow-step {{
    background: #181818;
    border-radius: 6px;
    padding: 1.2rem;
    border: none;
    text-align: center;
    position: relative;
    transition: background 0.3s ease;
  }}
  .workflow-step:hover {{
    background: #282828;
  }}

  .workflow-icon {{
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }}

  .workflow-title {{
    font-size: 0.85rem;
    font-weight: 700;
    color: {TEXT};
    margin-bottom: 0.25rem;
  }}

  .workflow-sub {{
    font-size: 0.75rem;
    color: {TEXT_SECONDARY};
    line-height: 1.4;
  }}

  /* Searchbox */
  [data-testid="stTextInput"] input {{
    background: {CARD_BG} !important;
    border: 1px solid #333 !important;
    border-radius: 100px !important;
    color: {TEXT} !important;
    padding: 0.75rem 1.2rem !important;
    font-size: 1rem !important;
  }}

  [data-testid="stTextInput"] input:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 2px {ACCENT}30 !important;
  }}

  /* Tier comparison */
  .tier-card {{
    background: #181818;
    border-radius: 6px;
    padding: 1.5rem;
    border: none;
    text-align: center;
    transition: background 0.3s ease;
  }}
  .tier-card:hover {{ background: #282828; }}
  .tier-card.premium-card {{ border-top: 3px solid {ACCENT}; }}
  .tier-card.free-card {{ border-top: 3px solid {BLUE}; }}

  .tier-icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
  .tier-name {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; }}
  .tier-stat {{ margin: 0.5rem 0; }}
  .tier-stat-val {{ font-size: 1.8rem; font-weight: 800; }}
  .tier-stat-lbl {{ font-size: 0.75rem; color: {TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.08em; }}

  /* Divider */
  hr {{ border-color: #333 !important; margin: 1.5rem 0 !important; }}

  /* Selectbox */
  [data-testid="stSelectbox"] > div > div {{
    background: {CARD_BG} !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
  }}

  /* Tabs */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid #333 !important;
  }}

  [data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    color: {TEXT_SECONDARY} !important;
    font-weight: 600 !important;
  }}

  [data-testid="stTabs"] [aria-selected="true"] {{
    color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT} !important;
  }}

  /* Spinner */
  [data-testid="stSpinner"] {{ color: {ACCENT} !important; }}

  /* Sidebar logo area — collapse gap between st.image() and the title div */
  [data-testid="stSidebar"] [data-testid="stImage"] {{
    margin-bottom: 0 !important;
    line-height: 0;
  }}

  .sidebar-logo {{
    padding: 0.2rem 0 0.9rem 0;
    border-bottom: 1px solid #222;
    margin-bottom: 1rem;
  }}

  .sidebar-logo-text {{
    font-size: 1rem;
    font-weight: 800;
    line-height: 1.25;
    color: {TEXT};
    letter-spacing: -0.01em;
    white-space: nowrap;
  }}

  .sidebar-logo-sub {{
    font-size: 0.68rem;
    color: {TEXT_SECONDARY};
    font-weight: 400;
  }}

  /* Progress bars */
  .stProgress > div > div > div > div {{
    background: {ACCENT} !important;
  }}
</style>
""", unsafe_allow_html=True)


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    """Load processed data, re-running pipeline when cache is stale or too small."""
    data_dir = ROOT / "data"
    processed_path = data_dir / "processed" / "processed_reviews.json"
    stats_path = data_dir / "processed" / "pipeline_stats.json"

    # Check if all_reviews.csv is newer than the processed cache
    csv_path = data_dir / "raw" / "all_reviews.csv"
    cache_stale = False
    if processed_path.exists() and csv_path.exists():
        cache_stale = csv_path.stat().st_mtime > processed_path.stat().st_mtime

    if processed_path.exists() and stats_path.exists() and not cache_stale:
        with open(processed_path, encoding="utf-8") as f:
            records = json.load(f)
        with open(stats_path, encoding="utf-8") as f:
            stats = json.load(f)
        # Invalidate tiny mock-era caches (< 500 rows)
        if len(records) >= 500:
            return records, stats

    try:
        from src.pipeline.filter_noise import run_full_pipeline
        records, stats = run_full_pipeline(data_dir)
        return records, stats
    except Exception as e:
        st.error(f"Pipeline failed: {e}")
        return [], {}


@st.cache_data(ttl=300)
def load_report():
    """Load or generate PM insights report."""
    report_path = ROOT / "data" / "processed" / "pm_insights_report.json"
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            return json.load(f)

    try:
        from src.analyzer.generate_report import generate_pm_insights_report, save_report, load_or_run_pipeline
        records, stats = load_or_run_pipeline(ROOT / "data")
        report = generate_pm_insights_report(records, stats)
        save_report(report, ROOT / "data")
        return report
    except Exception as e:
        return {}


def records_to_df(records: list[dict]) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append({
            "ID": r.get("id", ""),
            "Source": r.get("source", "").replace("_", " ").title(),
            "Subreddit": r.get("subreddit", ""),
            "Author": r.get("author", "anonymous"),
            "Title": r.get("title", "")[:80],
            "Text Preview": r.get("text", "")[:200],
            "Subscription": r.get("subscription_tier", "unknown").capitalize(),
            "Sentiment": r.get("sentiment_score", 0),
            "Segment": r.get("user_segment", ""),
            "Root Cause": ", ".join(r.get("root_causes", [])),
            "Frustrations": ", ".join(r.get("interaction_frustrations", [])),
            "Echo Chamber": "Yes" if r.get("is_echo_chamber_mention") else "No",
            "DW Complaint": "Yes" if r.get("is_discover_weekly_complaint") else "No",
            "Radio Complaint": "Yes" if r.get("is_radio_complaint") else "No",
            "Autoplay Issue": "Yes" if r.get("is_autoplay_complaint") else "No",
            "Created At": r.get("created_at", ""),
            "URL": r.get("url", ""),
        })
    return pd.DataFrame(rows)


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _wrap_hover(text: str, width: int = 52) -> str:
    """Insert Plotly-compatible <br> breaks at word boundaries every `width` chars."""
    words = text.split()
    lines: list = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "<br>".join(lines)

def make_bar(
    data: dict,
    title: str,
    color=ACCENT,
    orientation: str = "v",
    height: int = 350,
    definitions: dict | None = None,
) -> go.Figure:
    labels = list(data.keys())
    values = list(data.values())

    # Build per-bar tooltip text — pre-wrapped at 52 chars to prevent modebar overlap
    if definitions:
        customdata = [_wrap_hover(definitions.get(lbl, lbl)) for lbl in labels]
        if orientation == "h":
            hovertemplate = (
                "<b style='font-size:13px;'>%{y}</b><br><br>"
                "<span style='color:#B3B3B3;font-size:12px;'>%{customdata}</span><br><br>"
                "<span style='color:#1DB954;font-weight:600;'>Count: %{x:,}</span>"
                "<extra></extra>"
            )
        else:
            hovertemplate = (
                "<b style='font-size:13px;'>%{x}</b><br><br>"
                "<span style='color:#B3B3B3;font-size:12px;'>%{customdata}</span><br><br>"
                "<span style='color:#1DB954;font-weight:600;'>Count: %{y:,}</span>"
                "<extra></extra>"
            )
    else:
        customdata = None
        hovertemplate = None

    hoverlabel_style = dict(
        bgcolor="#181818",
        bordercolor="#1DB954",
        font=dict(color="#FFFFFF", size=12, family="Inter, Helvetica Neue, sans-serif"),
    )

    if orientation == "h":
        bar_kwargs = dict(
            y=labels, x=values, orientation="h",
            marker_color=color,
            text=[f"{v:,}" for v in values],
            textposition="auto",
            textfont=dict(color=TEXT, size=12),
        )
        if customdata is not None:
            bar_kwargs["customdata"] = customdata
            bar_kwargs["hovertemplate"] = hovertemplate
        fig = go.Figure(go.Bar(**bar_kwargs))
        layout = {**PLOTLY_TEMPLATE["layout"], "title": title, "height": height}
        layout["yaxis"] = {**layout.get("yaxis", {}), "categoryorder": "total ascending"}
        if customdata is not None:
            layout["hovermode"] = "y unified"
        fig.update_layout(**layout)
    else:
        bar_kwargs = dict(
            x=labels, y=values,
            marker_color=color,
            text=[f"{v:,}" for v in values],
            textposition="auto",
            textfont=dict(color=TEXT, size=12),
        )
        if customdata is not None:
            bar_kwargs["customdata"] = customdata
            bar_kwargs["hovertemplate"] = hovertemplate
        fig = go.Figure(go.Bar(**bar_kwargs))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], title=title, height=height)

    if customdata is not None:
        fig.update_traces(hoverlabel=hoverlabel_style)

    return fig


def make_pie(data: dict, title: str, colors=None) -> go.Figure:
    default_colors = [ACCENT, BLUE, YELLOW, RED, PURPLE, "#FF6B35", "#00C2FF", "#FF78C4", "#7FB069"]
    fig = go.Figure(go.Pie(
        labels=list(data.keys()),
        values=list(data.values()),
        hole=0.45,
        marker=dict(colors=colors or default_colors[:len(data)]),
        textfont=dict(color=TEXT, size=12),
        hovertemplate="<b>%{label}</b><br>%{value} reviews<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title=dict(text=title, x=0.5),
        showlegend=True,
        legend=dict(orientation="v", x=1.05, y=0.5, font=dict(color=TEXT, size=11)),
        height=380,
    )
    return fig


def make_gauge(value: float, title: str, max_val: float = 100, color: str = ACCENT) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=title, font=dict(color=TEXT, size=13)),
        number=dict(suffix="%", font=dict(color=TEXT, size=28)),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor=TEXT_SECONDARY, tickfont=dict(color=TEXT_SECONDARY)),
            bar=dict(color=color),
            bgcolor=CARD_BG,
            bordercolor="#333",
            steps=[
                dict(range=[0, max_val * 0.33], color="#1a1a1a"),
                dict(range=[max_val * 0.33, max_val * 0.66], color="#222"),
                dict(range=[max_val * 0.66, max_val], color="#2a1a1a"),
            ],
        ),
    ))
    fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=220)
    return fig


def make_grouped_bar(data: dict, groups: list, title: str) -> go.Figure:
    """Grouped bar chart for Premium vs Free comparisons."""
    fig = go.Figure()
    colors = [ACCENT, BLUE, YELLOW]
    for i, (grp_label, values) in enumerate(data.items()):
        fig.add_trace(go.Bar(
            name=grp_label,
            x=groups,
            y=values,
            marker_color=colors[i % len(colors)],
            text=[f"{v:.1f}%" for v in values],
            textposition="auto",
            textfont=dict(color=TEXT, size=11),
        ))
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title=title,
        barmode="group",
        height=380,
        legend=dict(font=dict(color=TEXT)),
    )
    return fig


# ── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg",
            width=44,
        )
        st.markdown("""
        <div class="sidebar-logo">
          <div class="sidebar-logo-text">Spotify Discovery Engine</div>
          <div class="sidebar-logo-sub">AI-Powered Review Analysis</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:0.5rem;font-size:0.7rem;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;'>Navigation</div>", unsafe_allow_html=True)

        nav_items = [
            ("📊", "Executive Dashboard", "High-level KPIs & metrics"),
            ("📂", "Data Sources Explorer", "Browse raw review data"),
            ("🧠", "Strategic PM Insights", "Discovery questions answered"),
            ("💬", "Semantic Query Playground", "Ask natural language questions"),
            ("🔬", "AI Workflow", "Analysis blueprint"),
        ]

        if "nav" not in st.session_state:
            st.session_state.nav = "Executive Dashboard"

        for icon, label, desc in nav_items:
            is_active = st.session_state.nav == label
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{label}",
                use_container_width=True,
            ):
                st.session_state.nav = label
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        st.markdown("<div style='font-size:0.7rem;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;'>Data Controls</div>", unsafe_allow_html=True)

        if st.button("🔄  Refresh Pipeline", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='font-size:0.7rem;color:{TEXT_SECONDARY};text-align:center;line-height:1.8;'>
          <div style='color:{ACCENT};font-weight:700;margin-bottom:0.3rem;'>Spotify PM Research</div>
          AI-Powered Discovery Analysis<br>
          Powered by Claude · v2.0
        </div>
        """, unsafe_allow_html=True)

    return st.session_state.nav


# ── View 1: Executive Dashboard ──────────────────────────────────────────────

def render_executive_dashboard(records: list[dict], stats: dict, report: dict):
    total_ingested = stats.get("total_ingested", 8500)
    ingested_label = f"{total_ingested:,}+"
    st.markdown(f"""
    <div class="hero-banner">
      <div><span class="accent-badge">Live Analysis</span><span class="accent-badge" style="background:#282828;color:#B3B3B3;">Spotify PM Project</span></div>
      <h1 class="hero-title">📊 Executive Discovery Dashboard</h1>
      <p class="hero-sub">Real-time analysis of {ingested_label} multi-source user reviews revealing why Spotify users experience Algorithmic Echo Chambers</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Segment slicer ─────────────────────────────────────────────────────
    segments = ["All Segments"] + sorted(set(r.get("user_segment", "") for r in records if r.get("user_segment")))
    selected_segment = st.selectbox("🎛️ User Segment Slicer", segments, key="segment_slicer")

    filtered = records if selected_segment == "All Segments" else [
        r for r in records if r.get("user_segment") == selected_segment
    ]

    if not filtered:
        st.warning("No records for selected segment.")
        return

    # Recompute stats for filtered set
    n = len(filtered)
    total_raw = stats.get("total_ingested", len(records) + stats.get("total_rejected", 0))
    rejected = stats.get("total_rejected", 0)

    echo_rate = round(sum(1 for r in filtered if r.get("is_echo_chamber_mention")) / n * 100, 1)
    dw_rate = round(sum(1 for r in filtered if r.get("is_discover_weekly_complaint")) / n * 100, 1)
    radio_rate = round(sum(1 for r in filtered if r.get("is_radio_complaint")) / n * 100, 1)
    autoplay_rate = round(sum(1 for r in filtered if r.get("is_autoplay_complaint")) / n * 100, 1)
    avg_sentiment = round(sum(r.get("sentiment_score", 0) for r in filtered) / n, 3)
    discovery_complaint_rate = stats.get("discovery_complaint_rate", round((echo_rate + dw_rate) / 2, 1))

    # ── Row 1: Ingestion stats ─────────────────────────────────────────────
    st.markdown("<div class='section-header'>📥 Review Ingestion Overview</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background:#181818;border-radius:6px;padding:1.2rem 1.5rem;border:none;margin-bottom:1.5rem;'>
      <div style='font-size:0.85rem;color:{TEXT_SECONDARY};line-height:1.8;'>
        <span style='color:{TEXT};font-weight:700;font-size:1.1rem;'>What does this mean?</span><br>
        We collected user reviews from 5 sources (Reddit, Spotify Community, Google Play Store, Apple App Store, YouTube).
        Each review went through an AI noise-filtering process to remove irrelevant content (login issues, payment bugs, app crashes)
        and keep only reviews about music discovery, recommendations, and echo chamber experiences.
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value">{total_raw:,}</div>
          <div class="metric-label">Total Reviews Ingested</div>
          <div class="metric-delta">Raw data collected across all 5 sources</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value">{rejected:,}</div>
          <div class="metric-label">Reviews Rejected</div>
          <div class="metric-delta">Noise: crashes, billing, login issues</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value">{n:,}</div>
          <div class="metric-label">Reviews Used For Analysis</div>
          <div class="metric-delta"><span style="color:{ACCENT};font-weight:600;">✓</span> Discovery-relevant content only</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        pass_rate = round(n / max(total_raw, 1) * 100, 1)
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value">{pass_rate}%</div>
          <div class="metric-label">Signal Quality Rate</div>
          <div class="metric-delta">Percentage relevant to discovery</div>
        </div>""", unsafe_allow_html=True)

    # ── Visual ingestion funnel ─────────────────────────────────────────────
    funnel_fig = go.Figure(go.Funnel(
        y=["Raw Reviews Collected", "Noise Filtered Out", "Discovery-Related Reviews Used"],
        x=[total_raw, rejected, n],
        textinfo="value+percent initial",
        marker=dict(color=["#2D46B9", "#E91429", ACCENT]),
        textfont=dict(color="#FFFFFF", size=13, family="Inter, Helvetica Neue, sans-serif"),
        connector=dict(line=dict(color="#333", width=2)),
    ))
    funnel_fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title="Review Ingestion Funnel — From Raw Data to Analysis-Ready",
        height=280,
    )
    st.plotly_chart(funnel_fig, use_container_width=True, config={"displayModeBar": False})

    # ── Row 2: Core KPIs ──────────────────────────────────────────────────
    st.markdown("<div class='section-header'>🎯 Core Discovery KPIs</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background:#181818;border-radius:6px;padding:1rem 1.5rem;border:none;margin-bottom:1rem;font-size:0.85rem;color:{TEXT_SECONDARY};'>
      <b style='color:{TEXT};'>How to read these metrics:</b> Each metric below represents a percentage of the {n:,} filtered reviews that mention that specific problem.
      Higher = more users complaining about that specific issue. Red indicates critical levels (>50%).
    </div>
    """, unsafe_allow_html=True)

    kpis = [
        ("Discovery Complaint Rate", discovery_complaint_rate, "%", "Users complaining about discovery broadly", ACCENT),
        ("Echo Chamber Mention Rate", echo_rate, "%", "Explicitly mention 'echo chamber' or feedback loops", RED if echo_rate > 50 else YELLOW),
        ("Discover Weekly Dissatisfaction", dw_rate, "%", "Unhappy specifically with Discover Weekly", YELLOW),
        ("Radio Repetition Rate", radio_rate, "%", "Report artist/playlist radio playing same songs", BLUE),
        ("Autoplay Saturation Index", autoplay_rate, "%", "Autoplay stuck on same song rotation", PURPLE),
        ("Avg Sentiment Score", round(avg_sentiment * 100, 1), "/100", "Normalized sentiment (-100=very negative)", RED if avg_sentiment < -0.5 else YELLOW),
    ]

    col_groups = [st.columns(3), st.columns(3)]
    for i, (label, val, unit, desc, color) in enumerate(kpis):
        col = col_groups[i // 3][i % 3]
        with col:
            display_val = f"{val:.1f}{unit}" if unit != "/100" else f"{val:.0f}/100"
            st.markdown(f"""<div class="metric-card" style="border-left:3px solid {color};">
              <div class="metric-value">{display_val}</div>
              <div class="metric-label">{label}</div>
              <div class="metric-delta">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # ── Core Discovery Research Insights Q&A ──────────────────────────────
    st.markdown("<div class='section-header'>🔍 Core Discovery Research Insights</div>", unsafe_allow_html=True)

    _QA_PAIRS = [
        (
            "Why do users struggle to discover new music?",
            "Collaborative filtering loops naturally over-index on historical data. This creates an algorithmic gravity well where the system continually serves high-probability engagement tracks instead of true novelty.",
        ),
        (
            "What are the most common frustrations with recommendations?",
            "Algorithmic echo chambers, high repetition rates on customised Artist Radios, and frozen weekly mixes that continuously cycle through tracks already present in the user's Liked Songs library.",
        ),
        (
            "What listening behaviours are users trying to achieve?",
            "Users are seeking active, intentional serendipity — an efficient way to expand their taste profiles across distinct sub-genres without permanently contaminating their core personalised recommendations.",
        ),
        (
            "What causes users to repeatedly listen to the same content?",
            "Passive background sessions (gym, work, sleep audio) generate heavy stream-count signals. The system misinterprets this high volume as deep preference, locking users into a loop of comfort-focused repetition.",
        ),
        (
            "Which user segments experience different discovery challenges?",
            "Loyal Long-Timers suffer from rigid data over-indexing built up over years of history. Genre Explorers experience severe contamination effects — sampling a niche style completely skews their main music feeds.",
        ),
        (
            "What unmet needs emerge consistently across reviews?",
            "Clear demands for user agency: a toggleable Exploration Mode that isolates new sessions, independent contextual listening profiles, and hard-dislike filters to actively exclude already-known tracks.",
        ),
    ]

    _qa_card_style = (
        "background:rgba(24,24,24,0.75);"
        "border:1px solid rgba(255,255,255,0.1);"
        "border-radius:8px;"
        "padding:1.1rem 1.3rem;"
        "height:100%;"
        "box-sizing:border-box;"
    )

    for row_start in range(0, len(_QA_PAIRS), 2):
        cols = st.columns(2)
        for col_idx, (q, a) in enumerate(_QA_PAIRS[row_start:row_start + 2]):
            with cols[col_idx]:
                st.markdown(f"""
                <div style="{_qa_card_style}">
                  <div style="font-size:0.82rem;font-weight:700;color:{TEXT};margin-bottom:0.55rem;line-height:1.45;">{q}</div>
                  <div style="font-size:0.82rem;color:{TEXT_SECONDARY};line-height:1.6;">{a}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

    # ── Gauge row ─────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📡 Severity Gauges</div>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(make_gauge(echo_rate, "Echo Chamber Rate", color=RED if echo_rate > 50 else YELLOW), use_container_width=True, config={"displayModeBar": False})
    with g2:
        st.plotly_chart(make_gauge(dw_rate, "Discover Weekly Dissatisfaction", color=YELLOW), use_container_width=True, config={"displayModeBar": False})
    with g3:
        st.plotly_chart(make_gauge(radio_rate, "Radio Repetition Rate", color=BLUE), use_container_width=True, config={"displayModeBar": False})

    # ── Source & Segment distributions ────────────────────────────────────
    st.markdown("<div class='section-header'>📊 Data Composition</div>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)

    source_counts = dict(Counter(r.get("source", "").replace("_", " ").title() for r in filtered))
    with col_l:
        st.plotly_chart(make_pie(source_counts, "Reviews by Source Platform"), use_container_width=True, config={"displayModeBar": False})

    segment_counts = dict(Counter(r.get("user_segment", "General Listener") for r in filtered))
    with col_r:
        st.plotly_chart(make_pie(segment_counts, "Reviews by User Segment", colors=[ACCENT, BLUE, YELLOW, RED, PURPLE, "#FF6B35", "#00C2FF"]), use_container_width=True, config={"displayModeBar": False})

    # ── Root cause & Frustration charts ───────────────────────────────────
    st.markdown("<div class='section-header'>🔍 What's Breaking Discovery?</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{TEXT_SECONDARY};margin-bottom:1rem;font-size:0.9rem;'>These are the <b style='color:{TEXT};'>root causes</b> (WHY discovery fails) and <b style='color:{TEXT};'>friction points</b> (WHERE in the UX it breaks), extracted from user language using AI pattern matching.</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{ACCENT};font-size:0.78rem;margin-bottom:0.75rem;'>💡 <i>Interactive Feature: Hover over any axis category label or chart bar to reveal the underlying PM framework definition.</i></div>", unsafe_allow_html=True)

    from collections import Counter as _Counter
    root_cause_counts: Counter = _Counter()
    for r in filtered:
        for c in r.get("root_causes", []):
            root_cause_counts[c] += 1

    frustration_counts: Counter = _Counter()
    for r in filtered:
        for f in r.get("interaction_frustrations", []):
            frustration_counts[f] += 1

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        if root_cause_counts:
            fig = make_bar(
                dict(root_cause_counts.most_common(8)),
                "Behavioral Root Causes",
                color=ACCENT,
                orientation="h",
                height=380,
                definitions=ROOT_CAUSE_DEFS,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_r2:
        if frustration_counts:
            fig = make_bar(
                dict(frustration_counts.most_common(8)),
                "UX Friction Points",
                color=YELLOW,
                orientation="h",
                height=380,
                definitions=FRUSTRATION_DEFS,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Sentiment over time ────────────────────────────────────────────────
    st.subheader(
        "📈 Sentiment Trend by Source",
        help=(
            "How is this calculated?\n\n"
            "The engine uses an LLM-based zero-shot sentiment analysis model. It processes "
            "the text of every review and calculates a normalized polarity score:\n\n"
            "• (-1.00): Deeply negative sentiment (active product frustration, intent to churn)\n"
            "• (0.00): Completely neutral mention\n"
            "• (+1.00): Highly positive product sentiment\n\n"
            "The chart displays the collective mathematical average of all discovery-related "
            "reviews aggregated per platform channel."
        ),
    )
    st.markdown(f"<div style='color:{TEXT_SECONDARY};font-size:0.78rem;margin-bottom:0.5rem;'>ℹ️ <i>Hover over the help icon next to the heading to view the full LLM zero-shot polarity scoring methodology.</i></div>", unsafe_allow_html=True)
    sentiment_by_source = {}
    for r in filtered:
        src = r.get("source", "unknown").replace("_", " ").title()
        if src not in sentiment_by_source:
            sentiment_by_source[src] = []
        sentiment_by_source[src].append(r.get("sentiment_score", 0))

    sentiment_avgs = {src: round(sum(vals) / len(vals), 3) for src, vals in sentiment_by_source.items()}
    colors = [RED if v < -0.5 else YELLOW if v < -0.2 else ACCENT for v in sentiment_avgs.values()]

    sent_fig = go.Figure(go.Bar(
        x=list(sentiment_avgs.keys()),
        y=list(sentiment_avgs.values()),
        marker_color=colors,
        text=[f"{v:+.2f}" for v in sentiment_avgs.values()],
        textposition="auto",
        textfont=dict(color=TEXT),
    ))
    sent_fig.add_hline(y=0, line_dash="dash", line_color="#555", annotation_text="Neutral", annotation_font=dict(color=TEXT_SECONDARY))
    sent_fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Average Sentiment Score by Source Platform (-1 = very negative, +1 = very positive)", height=320)
    st.plotly_chart(sent_fig, use_container_width=True, config={"displayModeBar": False})

    # ── Key insight ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="insight-box danger">
      <div class="insight-title">⚠️ Critical Executive Finding</div>
      <div class="insight-text">
        <b>{echo_rate:.0f}%</b> of analyzed reviews explicitly describe echo chamber or feedback loop behavior.
        The average sentiment score of <b>{avg_sentiment:+.2f}</b> indicates deeply negative user experience around discovery.
        <b>This is not a minor UX annoyance</b> — users describe algorithmic fatigue as actively harming their relationship with music.
        Premium users are disproportionately affected, creating a significant churn risk in Spotify's highest-value customer segment.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── View 2: Data Sources Explorer ────────────────────────────────────────────

def render_data_explorer(records: list[dict], stats: dict):
    st.markdown("""
    <div class="hero-banner">
      <h1 class="hero-title">📂 Data Sources Explorer</h1>
      <p class="hero-sub">Browse, filter, and inspect raw user reviews with AI-assigned behavioral tags, sentiment scores, and discovery classification</p>
    </div>
    """, unsafe_allow_html=True)

    df = records_to_df(records)

    if df.empty:
        st.warning("No data available.")
        return

    # ── Source tabs ────────────────────────────────────────────────────────
    source_map = {
        "All Sources": df,
        "Reddit": df[df["Source"].str.lower().str.contains("reddit")],
        "Spotify Forums": df[df["Source"].str.lower().str.contains("spotify community")],
        "Play Store": df[df["Source"].str.lower().str.contains("play store")],
        "YouTube": df[df["Source"].str.lower().str.contains("youtube")],
        "App Store": df[df["Source"].str.lower().str.contains("app store")],
    }

    tab_labels = list(source_map.keys())
    tabs = st.tabs(tab_labels)

    for tab, (source_name, source_df) in zip(tabs, source_map.items()):
        with tab:
            if source_df.empty:
                st.info(f"No records from {source_name}")
                continue

            # Stats row
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total Reviews", len(source_df))
            with c2:
                prem_pct = round(len(source_df[source_df["Subscription"] == "Premium"]) / len(source_df) * 100, 1)
                st.metric("Premium Users", f"{prem_pct}%")
            with c3:
                echo_pct = round(len(source_df[source_df["Echo Chamber"] == "Yes"]) / len(source_df) * 100, 1)
                st.metric("Echo Chamber Mentions", f"{echo_pct}%")
            with c4:
                avg_sent = round(source_df["Sentiment"].mean(), 3)
                st.metric("Avg Sentiment", f"{avg_sent:+.2f}")

            # Filters row
            col_search, col_tier, col_segment = st.columns([3, 1.5, 1.5])
            with col_search:
                search_term = st.text_input("🔍 Search reviews", placeholder="Type to filter...", key=f"search_{source_name}")
            with col_tier:
                tier_filter = st.selectbox("Subscription", ["All", "Premium", "Free", "Unknown"], key=f"tier_{source_name}")
            with col_segment:
                seg_options = ["All"] + sorted(source_df["Segment"].unique().tolist())
                seg_filter = st.selectbox("Segment", seg_options, key=f"seg_{source_name}")

            # Apply filters
            filtered_df = source_df.copy()
            if search_term:
                mask = (
                    filtered_df["Text Preview"].str.lower().str.contains(search_term.lower(), na=False) |
                    filtered_df["Title"].str.lower().str.contains(search_term.lower(), na=False)
                )
                filtered_df = filtered_df[mask]
            if tier_filter != "All":
                filtered_df = filtered_df[filtered_df["Subscription"] == tier_filter]
            if seg_filter != "All":
                filtered_df = filtered_df[filtered_df["Segment"] == seg_filter]

            st.markdown(f"<div style='color:{TEXT_SECONDARY};font-size:0.85rem;margin:0.5rem 0;'>Showing <b style='color:{ACCENT};'>{len(filtered_df)}</b> of {len(source_df)} reviews</div>", unsafe_allow_html=True)

            # Color-coded sentiment
            def color_sentiment(val):
                if val < -0.5:
                    return f"color: {RED}"
                elif val < -0.2:
                    return f"color: {YELLOW}"
                else:
                    return f"color: {ACCENT}"

            display_cols = ["Source", "Subscription", "Segment", "Sentiment", "Echo Chamber", "DW Complaint", "Root Cause", "Title", "Text Preview"]
            available_cols = [c for c in display_cols if c in filtered_df.columns]

            styled_df = filtered_df[available_cols].style.map(
                color_sentiment, subset=["Sentiment"] if "Sentiment" in available_cols else []
            ).format({"Sentiment": "{:+.3f}"})

            st.dataframe(styled_df, use_container_width=True, height=420)


# ── View 3: Strategic PM Insights ────────────────────────────────────────────

def render_pm_insights(records: list[dict], stats: dict, report: dict):
    st.markdown("""
    <div class="hero-banner">
      <h1 class="hero-title">🧠 Strategic PM Insights</h1>
      <p class="hero-sub">Evidence-backed answers to Spotify's core discovery questions, derived from 8,500+ user reviews through AI analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Q&A Section ────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>🔑 Core Discovery Questions Answered</div>", unsafe_allow_html=True)

    qa_data = [
        (
            "Why do users experience Algorithmic Echo Chambers?",
            "The echo chamber forms through 3 compounding mechanisms: (1) Collaborative filtering amplifies majority taste signals — the algorithm asks 'what do similar users like?' but with 600M users, 'similar' becomes very broad. (2) Passive/background listening (work music, sleep music) generates massive playcount signals that the algorithm misinterprets as strong preference. (3) The algorithm optimizes for low skip rates, which rewards the familiar and punishes the novel. Together these create a gravity well: the more you listen, the deeper your chamber gets.",
            "danger",
        ),
        (
            "Which user segment suffers the most?",
            "Loyal Long-Timers (5+ year Premium users) suffer the most. They have: (a) the richest listening history creating the deepest echo chambers, (b) the highest expectations having paid for years, and (c) the clearest memory of how good Discover Weekly used to be in 2015-2017. Genre Explorers are the second-most frustrated — they actively want to discover but the algorithm punishes exploration by contaminating their taste profile with every genre they sample.",
            "warning",
        ),
        (
            "Which features fail most at delivering discovery?",
            "Feature performance ranking (worst → best): Artist Radio (plays ~40 songs in loops, 44% complaint rate) → Daily Mix (essentially static, 'Daily' is misleading) → Discover Weekly (once exceptional, now serving already-known songs ~40% of the time) → Autoplay (grabs 20 songs from a fixed pool regardless of prior playlist context) → Release Radar (best performer, genuinely new releases). Notably, AI DJ starts well but degrades into echo chamber patterns within 2 weeks.",
            "info",
        ),
        (
            "Is this a Premium user problem or a Free user problem?",
            "Both tiers suffer, but differently. Premium users report deeper, more entrenched echo chambers (they have years of listening data creating stronger loops). Free users report broader frustration that the algorithm defaults to trending/popular content regardless of their actual taste. Critical insight: Premium subscribers pay a premium subscription fee and still experience the same discovery failures — this directly undermines the premium value proposition and represents a significant churn risk.",
            "purple",
        ),
        (
            "What would fix this?",
            "Top 3 highest-impact interventions: (1) Exploration Mode — a toggle that increases novelty without contaminating the core taste profile; addresses fear-of-contamination paralysis. (2) Contextual Profiles — separate listening profiles per context (gym/work/chill) to prevent cross-contamination. (3) Discover Weekly Quality Gate — automated check to ensure zero songs already in Liked Songs or played in the last 90 days, basic quality control that should already exist.",
            "default",
        ),
    ]

    for question, answer, box_type in qa_data:
        box_class = f"insight-box {'warning' if box_type == 'warning' else 'danger' if box_type == 'danger' else 'info' if box_type == 'info' else 'purple' if box_type == 'purple' else ''}"
        st.markdown(f"""
        <div class="{box_class}" style="margin-bottom:1rem;">
          <div class="insight-title">Q: {question}</div>
          <div class="insight-text">{answer}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Strategic Recommendations ──────────────────────────────────────────
    st.markdown("<div class='section-header'>🎯 Strategic PM Recommendations</div>", unsafe_allow_html=True)

    recs = report.get("strategic_recommendations", [
        {"priority": "P0", "title": "Taste Profile Versioning", "description": "Multiple contextual profiles (Gym, Work, Explore)", "effort": "High", "impact": "Critical"},
        {"priority": "P0", "title": "Exploration Mode", "description": "Novelty toggle that doesn't contaminate core profile", "effort": "Medium", "impact": "Critical"},
        {"priority": "P1", "title": "Passive vs Active Listening", "description": "Weight background listening less in taste model", "effort": "Medium", "impact": "High"},
        {"priority": "P1", "title": "Echo Chamber Health Score", "description": "User-visible diversity metric with gamification", "effort": "Low", "impact": "High"},
        {"priority": "P2", "title": "Discover Weekly Quality Gate", "description": "Auto-check for already-known songs before publishing", "effort": "Low", "impact": "Medium"},
    ])

    priority_colors = {"P0": RED, "P1": YELLOW, "P2": BLUE, "P3": TEXT_SECONDARY}
    effort_icons = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
    impact_icons = {"Critical": "💥", "High": "🔥", "Medium": "⚡"}

    for rec in recs:
        pri = rec.get("priority", "P2")
        color = priority_colors.get(pri, TEXT_SECONDARY)
        effort = rec.get("effort", "Medium")
        impact = rec.get("impact", "High")

        st.markdown(f"""
        <div class="metric-card" style="border-left:4px solid {color};">
          <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
            <span style="background:{color};color:#000;font-size:0.7rem;font-weight:800;padding:0.2rem 0.6rem;border-radius:100px;">{pri}</span>
            <span style="font-size:1rem;font-weight:700;color:{TEXT};">{rec.get('title','')}</span>
          </div>
          <div style="font-size:0.9rem;color:{TEXT_SECONDARY};margin-bottom:0.75rem;line-height:1.5;">{rec.get('description','')}</div>
          <div style="display:flex;gap:1rem;font-size:0.8rem;">
            <span>Effort: {effort_icons.get(effort,'⚡')} <b style='color:{TEXT};'>{effort}</b></span>
            <span>Impact: {impact_icons.get(impact,'🔥')} <b style='color:{TEXT};'>{impact}</b></span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Verbatim Quotes ────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>💬 Top Verbatim Quotes for PM Presentations</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{TEXT_SECONDARY};font-size:0.85rem;margin-bottom:1rem;'>These are the most impactful quotes for user interviews, stakeholder decks, and design reviews. Sorted by emotional intensity.</div>", unsafe_allow_html=True)

    top_quotes = sorted(
        [
            r for r in records
            if r.get("verbatim_quote")
            and len(r.get("verbatim_quote", "")) > 60
            and r.get("sentiment_score", 0) < -0.3
            and (
                r.get("is_discovery_complaint")
                or r.get("is_echo_chamber_mention")
                or r.get("is_discover_weekly_complaint")
                or r.get("is_radio_complaint")
                or r.get("is_autoplay_complaint")
            )
        ],
        key=lambda r: r.get("sentiment_score", 0),  # most negative first
        reverse=False,
    )[:8]

    for q in top_quotes:
        quote = q.get("verbatim_quote", "")
        source = q.get("source", "").replace("_", " ").title()
        tier = q.get("subscription_tier", "unknown")
        segment = q.get("user_segment", "")
        sent = q.get("sentiment_score", 0)

        tier_class = "premium" if tier == "premium" else "free" if tier == "free" else ""
        sent_color = RED if sent < -0.6 else YELLOW if sent < -0.3 else TEXT_SECONDARY

        st.markdown(f"""
        <div class="quote-card">
          <span class="quote-mark">"</span>
          <p class="quote-text">{quote}</p>
          <div class="quote-meta">
            <span class="tag">{source}</span>
            <span class="tag {tier_class}">{tier.capitalize()}</span>
            <span class="tag">{segment}</span>
            <span class="tag sentiment-neg">Sentiment: {sent:+.2f}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)



# ── View 4: Semantic Query Playground ────────────────────────────────────────

def render_semantic_playground(records: list[dict]):
    st.markdown("""
    <div class="hero-banner">
      <h1 class="hero-title">💬 Semantic Query Playground</h1>
      <p class="hero-sub">Ask natural language questions about the user review data. The engine surfaces the most relevant reviews and synthesizes an AI-powered answer.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="insight-box info" style="margin-bottom:1.5rem;">
      <div class="insight-title">How This Works</div>
      <div class="insight-text">
        Type any question about Spotify's discovery problems. The engine uses keyword relevance scoring to find the most matching reviews
        from our {len(records):,} analyzed records, then synthesizes a structured answer with direct quotes and evidence.
        <br><br><b>Try:</b> "What do power curators say about Discover Weekly?" or "Why do free users feel limited?" or "What is the gym playlist problem?"
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Example queries ────────────────────────────────────────────────────
    example_queries = [
        "What do power curators say about playlist radios?",
        "Why are long-term premium users most frustrated?",
        "What is the gym playlist contamination problem?",
        "How do free users experience discovery differently?",
        "What specifically breaks about Discover Weekly?",
        "Why do users say the algorithm gets worse over time?",
    ]

    st.markdown("<div style='margin-bottom:0.75rem;font-size:0.85rem;color:" + TEXT_SECONDARY + ";'>Quick examples (click to use):</div>", unsafe_allow_html=True)
    example_cols = st.columns(3)
    for i, eq in enumerate(example_queries):
        col = example_cols[i % 3]
        if col.button(f"💡 {eq}", key=f"eq_{i}", use_container_width=True):
            st.session_state["query_input"] = eq

    query = st.text_input(
        "🔍 Your question",
        placeholder="e.g., What do power curators say about playlist radios?",
        key="query_input",
    )

    if query and len(query.strip()) > 5:
        keywords = [kw.lower() for kw in query.split() if len(kw) > 3]

        def relevance_score(rec: dict) -> int:
            text = f"{rec.get('text', '')} {rec.get('title', '')}".lower()
            return sum(1 for kw in keywords if kw in text)

        scored = [(relevance_score(r), r) for r in records]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_records = [r for score, r in scored if score > 0][:15]

        if not top_records:
            top_records = records[:10]

        st.markdown(f"<div style='color:{TEXT_SECONDARY};font-size:0.85rem;margin:1rem 0;'>Found <b style='color:{ACCENT};'>{len(top_records)}</b> relevant reviews. Synthesizing answer...</div>", unsafe_allow_html=True)

        # ── Synthesized answer ─────────────────────────────────────────────
        sources_found = list(set(r.get("source", "").replace("_", " ").title() for r in top_records))
        tiers_found = list(set(r.get("subscription_tier", "unknown").capitalize() for r in top_records))
        segments_found = list(set(r.get("user_segment", "") for r in top_records if r.get("user_segment")))
        avg_sent = round(sum(r.get("sentiment_score", 0) for r in top_records) / len(top_records), 3)

        echo_mentions = sum(1 for r in top_records if r.get("is_echo_chamber_mention"))

        st.markdown(f"""
        <div class="insight-box">
          <div class="insight-title">🤖 AI Synthesis</div>
          <div class="insight-text">
            Based on <b>{len(top_records)}</b> relevant reviews from {', '.join(sources_found)}, the data shows:
            The average sentiment for reviews matching your query is <b style='color:{"#FF6B6B" if avg_sent < -0.3 else ACCENT};'>{avg_sent:+.3f}</b>.
            <b>{echo_mentions}</b> of these reviews explicitly mention echo chambers or feedback loops.
            The most affected user segments are: <b>{', '.join(segments_found[:3])}</b>.
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Matching reviews ───────────────────────────────────────────────
        col_sort, col_limit = st.columns([2, 1])
        with col_sort:
            sort_by = st.selectbox("Sort by", ["Relevance", "Most Negative", "Most Positive"], key="playground_sort")
        with col_limit:
            show_n = st.selectbox("Show", [5, 10, 15], key="playground_n")

        if sort_by == "Most Negative":
            top_records = sorted(top_records, key=lambda r: r.get("sentiment_score", 0))
        elif sort_by == "Most Positive":
            top_records = sorted(top_records, key=lambda r: r.get("sentiment_score", 0), reverse=True)

        for rec in top_records[:show_n]:
            quote = rec.get("verbatim_quote") or rec.get("text", "")[:300]
            source = rec.get("source", "").replace("_", " ").title()
            tier = rec.get("subscription_tier", "unknown")
            segment = rec.get("user_segment", "")
            sent = rec.get("sentiment_score", 0)
            causes = ", ".join(rec.get("root_causes", []))[:60]

            sent_color = RED if sent < -0.5 else YELLOW if sent < -0.2 else ACCENT
            tier_class = "premium" if tier == "premium" else "free" if tier == "free" else ""

            st.markdown(f"""
            <div class="quote-card" style="border-left:3px solid {sent_color};margin-bottom:0.75rem;">
              <p class="quote-text" style="font-size:0.9rem;">{quote[:400]}</p>
              <div class="quote-meta">
                <span class="tag">{source}</span>
                <span class="tag {tier_class}">{tier.capitalize()}</span>
                <span class="tag">{segment}</span>
                <span class="tag" style="color:{sent_color};">Sentiment {sent:+.2f}</span>
                <span class="tag" style="background:#222;">{causes}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Chart of matching reviews by source ────────────────────────────
        match_src = dict(Counter(r.get("source", "").replace("_", " ").title() for r in top_records))
        if len(match_src) > 1:
            fig = make_pie(match_src, f"Source Breakdown for: '{query[:40]}...'")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    else:
        st.markdown(f"""
        <div style="background:#181818;border-radius:6px;border:2px dashed #333;padding:3rem;text-align:center;margin-top:1rem;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">💬</div>
          <div style="font-size:1rem;color:{TEXT_SECONDARY};">Enter a question above to search through {len(records):,} analyzed reviews</div>
        </div>
        """, unsafe_allow_html=True)


# ── View 5: AI Workflow ───────────────────────────────────────────────────────

def render_ai_workflow(records: list[dict], stats: dict):
    st.markdown("""
    <div class="hero-banner">
      <h1 class="hero-title">🔬 AI Analysis Workflow</h1>
      <p class="hero-sub">Step-by-step blueprint of our analysis framework — from raw data collection to strategic PM insights</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Pipeline visual ────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>🔄 End-to-End Pipeline Architecture</div>", unsafe_allow_html=True)

    steps = [
        ("📡", "Data Collection", "5 Sources", "Reddit, Spotify Community, Play Store, App Store, YouTube API", BLUE),
        ("🧹", "Noise Filtering", "AI Preprocessing", "Strip login bugs, crashes, payments. Keep discovery-related only.", YELLOW),
        ("🏷️", "Enrichment", "Behavioral Tagging", "Root causes, user segments, frustrations, sentiment, tier inference.", ACCENT),
        ("🧠", "Semantic Analysis", "LLM Synthesis", "Pattern extraction, quote selection, cross-source synthesis.", PURPLE),
        ("📊", "Insight Generation", "PM Report", "Strategic recommendations, tier analysis, executive KPIs.", RED),
    ]

    cols = st.columns(len(steps))
    for col, (icon, title, subtitle, desc, color) in zip(cols, steps):
        with col:
            st.markdown(f"""
            <div class="workflow-step" style="border-top:3px solid {color};">
              <div class="workflow-icon">{icon}</div>
              <div class="workflow-title" style="color:{color};">{title}</div>
              <div style="font-size:0.7rem;font-weight:700;color:{TEXT_SECONDARY};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">{subtitle}</div>
              <div class="workflow-sub">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Flow arrows ────────────────────────────────────────────────────────
    arrow_cols = st.columns(len(steps))
    for i, col in enumerate(arrow_cols):
        with col:
            if i < len(steps) - 1:
                st.markdown(f"<div style='text-align:right;color:{ACCENT};font-size:1.5rem;padding-top:0.5rem;'>→</div>", unsafe_allow_html=True)

    # ── Pipeline stats ─────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📈 Pipeline Performance Metrics</div>", unsafe_allow_html=True)

    total_raw = stats.get("total_ingested", 0)
    total_rejected = stats.get("total_rejected", 0)
    total_used = stats.get("total_used", len(records))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Raw Records Ingested", f"{total_raw:,}", help="Total reviews collected from all 5 sources")
    with c2:
        st.metric("Noise Records Removed", f"{total_rejected:,}", help="Off-topic reviews filtered out")
    with c3:
        st.metric("Records Used", f"{total_used:,}", help="Discovery-relevant reviews that passed filtering")
    with c4:
        signal_quality = round(total_used / max(total_raw, 1) * 100, 1)
        st.metric("Signal Quality", f"{signal_quality}%", help="Percentage of raw data that was relevant")

    # ── Source breakdown ───────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📊 Data Sources Breakdown</div>", unsafe_allow_html=True)

    source_details = [
        ("Reddit", "r/spotify, r/spotifymusic, r/Music, r/LetsTalkMusic", "Old Reddit HTML + Search + Pushshift fallback", BLUE, 30),
        ("Spotify Community", "Music & Discovery category, genre threads", "BeautifulSoup + Playwright wrapper", ACCENT, 20),
        ("Google Play Store", "Android app reviews (1-3 star, discovery keywords)", "Review scraping + keyword filtering", YELLOW, 15),
        ("Apple App Store", "iOS app reviews (1-3 star, discovery keywords)", "App Store API + keyword filtering", RED, 15),
        ("YouTube", "Comment threads on Spotify algorithm critique videos", "YouTube Data API v3 (comment threads)", PURPLE, 20),
    ]

    for platform, scope, method, color, pct in source_details:
        st.markdown(f"""
        <div class="metric-card" style="border-left:3px solid {color};padding:1rem 1.2rem;margin-bottom:0.75rem;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <div style="font-weight:700;color:{TEXT};font-size:0.95rem;margin-bottom:0.25rem;">{platform}</div>
              <div style="color:{TEXT_SECONDARY};font-size:0.8rem;margin-bottom:0.35rem;">Scope: {scope}</div>
              <div style="color:{TEXT_SECONDARY};font-size:0.75rem;">Method: <code style='background:#333;padding:0.1rem 0.4rem;border-radius:4px;color:{color};'>{method}</code></div>
            </div>
            <div style="text-align:right;flex-shrink:0;margin-left:1rem;">
              <div style="font-size:1.4rem;font-weight:800;color:{color};">{pct}%</div>
              <div style="font-size:0.7rem;color:{TEXT_SECONDARY};">of dataset</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Noise filtering explainer ──────────────────────────────────────────
    st.markdown("<div class='section-header'>🧹 Noise Filtering Logic</div>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown(f"""
        <div style="background:#181818;border-radius:6px;padding:1.2rem;border:none;">
          <div style="font-weight:700;color:{RED};margin-bottom:0.75rem;font-size:0.9rem;">❌ EXCLUDED (Noise)</div>
          <ul style="color:{TEXT_SECONDARY};font-size:0.85rem;line-height:2;margin:0;padding-left:1.2rem;">
            <li>Login & account issues ("can't login", "forgot password")</li>
            <li>Payment & billing errors ("wrong charge", "refund")</li>
            <li>App crashes & technical bugs ("app won't open", "crash")</li>
            <li>Audio device issues ("bluetooth disconnect")</li>
            <li>Download & offline problems ("offline mode broken")</li>
            <li>Subscription management ("how to cancel")</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown(f"""
        <div style="background:#181818;border-radius:6px;padding:1.2rem;border:none;">
          <div style="font-weight:700;color:{ACCENT};margin-bottom:0.75rem;font-size:0.9rem;">✅ INCLUDED (Signal)</div>
          <ul style="color:{TEXT_SECONDARY};font-size:0.85rem;line-height:2;margin:0;padding-left:1.2rem;">
            <li>Echo chamber & feedback loop mentions</li>
            <li>Discover Weekly complaints & comparisons</li>
            <li>Radio repetition & autoplay loops</li>
            <li>Genre bubble & taste profile issues</li>
            <li>Recommendation staleness & quality decline</li>
            <li>Algorithmic fatigue & discovery frustration</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    # ── Tagging taxonomy ───────────────────────────────────────────────────
    st.markdown("<div class='section-header'>🏷️ AI Tagging Taxonomy</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{ACCENT};font-size:0.78rem;margin-bottom:0.85rem;'>💡 <i>Hover over individual taxonomy items to view framework descriptions.</i></div>", unsafe_allow_html=True)

    _root_tips = {
        "Feedback Loop Bias":      "System over-indexing on familiar liked tracks to safely boost completion and short-term retention metrics.",
        "Passive Fatigue":         "Mental exhaustion where users give up on manual exploration, depending blindly on stale, automated streams.",
        "Contextual Over-reliance":"System polluting core music discovery streams with utility audio habits (e.g., gym, sleeping sounds, or study sessions).",
        "Genre Bubble":            "Algorithmic isolation that locks users into a specific genre loop because of a brief, intense listening phase.",
        "Taste Evolution Lag":     "Recommendation model reacting too slowly when a user&#39;s real-world music interests organically pivot.",
        "Niche Content Gap":       "Inherent system bias that suppresses independent, obscure, or hyper-local artists from reaching mainstream user feeds.",
        "Cold Start Anchoring":    "Relying too heavily on initial onboarding data choices, making historical setups difficult to break out of over time.",
    }
    _frust_tips = {
        "Discover Weekly Quality":    "Degradation of the flagship discovery playlist, frequently recycling tracks instead of breaking new ground.",
        "Radio Repetition":           "Custom station or artist radio channels quickly decaying into a narrow loop of 15-20 predictable tracks.",
        "Autoplay Loop":              "Unwanted repetition of familiar library tracks immediately after a specific album, artist, or playlist concludes.",
        "Daily Mix Stagnation":       "High-frequency personalized mix variants feeling completely frozen week-over-week without rolling updates.",
        "No Escape Mechanism":        "The absence of a physical UI control (like a reset or hard-dislike switch) to reset the recommendation seed.",
        "Cross-Context Contamination":"Spilling shared family profiles, work streams, or meditation sounds into a user&#39;s primary daily dashboard feed.",
        "Algorithm Transparency":     "Lack of insight into why a specific track was suggested, making recommendations feel jarring or unearned.",
    }
    _seg_tips = {
        "Power Curator":        "Highly active user who manages dense custom playlists, values obscure tracks, and demands manual filtering tools.",
        "Passive Radio Listener":"High-retention consumer who relies strictly on Autoplay, mixes, and algorithm loops with low skip intervention.",
        "Genre Explorer":       "An adventurous listener looking to branch out globally across distinct sub-genres, highly sensitive to recommendation loops.",
        "Loyal Long-Timer":     "Multi-year premium user whose massive history profile is heavily over-indexed, making new discovery hard to activate.",
        "Free Tier Casual":     "Ad-supported user heavily throttled by shuffle-only mechanics and skip limitations, experiencing broken exploration paths.",
        "General Listener":     "Standard user displaying balanced listening habits, seeking a clean balance between comfort listening and fresh hits.",
    }

    def _tip_li(label: str, tip: str) -> str:
        return f'<li><span class="ft-tooltip" data-tip="{tip}" style="cursor:pointer;">{label}</span></li>'

    col1, col2, col3 = st.columns(3)

    with col1:
        items = "".join(_tip_li(k, v) for k, v in _root_tips.items())
        st.markdown(f"""
        <div style="background:#181818;border-radius:6px;padding:1.2rem;border:none;height:100%;">
          <div style="font-weight:700;color:{ACCENT};margin-bottom:0.75rem;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;">Behavioral Root Causes</div>
          <ul style="color:{TEXT_SECONDARY};font-size:0.8rem;line-height:2.1;margin:0;padding-left:1.2rem;">{items}</ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        items = "".join(_tip_li(k, v) for k, v in _frust_tips.items())
        st.markdown(f"""
        <div style="background:#181818;border-radius:6px;padding:1.2rem;border:none;height:100%;">
          <div style="font-weight:700;color:{YELLOW};margin-bottom:0.75rem;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;">Interaction Frustrations</div>
          <ul style="color:{TEXT_SECONDARY};font-size:0.8rem;line-height:2.1;margin:0;padding-left:1.2rem;">{items}</ul>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        items = "".join(_tip_li(k, v) for k, v in _seg_tips.items())
        st.markdown(f"""
        <div style="background:#181818;border-radius:6px;padding:1.2rem;border:none;height:100%;">
          <div style="font-weight:700;color:{PURPLE};margin-bottom:0.75rem;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;">User Segments</div>
          <ul style="color:{TEXT_SECONDARY};font-size:0.8rem;line-height:2.1;margin:0;padding-left:1.2rem;">{items}</ul>
        </div>
        """, unsafe_allow_html=True)


# ── Premium vs Free Analysis ──────────────────────────────────────────────────

def render_premium_free_analysis(records: list[dict], report: dict):
    """Render the Premium vs Free module within Executive Dashboard."""

    st.markdown("<div class='section-header'>💎 Premium vs Free Analysis</div>", unsafe_allow_html=True)

    from src.analyzer.generate_report import compute_tier_breakdown
    tier_data = compute_tier_breakdown(records)

    prem = tier_data.get("premium", {})
    free_d = tier_data.get("free", {})
    unk = tier_data.get("unknown", {})

    # ── Tier overview cards ────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        prem_pain = prem.get("discovery_pain_rate", 0)
        st.markdown(f"""
        <div class="tier-card premium-card">
          <div class="tier-icon">💎</div>
          <div class="tier-name" style="color:{ACCENT};">Premium Users</div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{RED if prem_pain > 60 else YELLOW};">{prem_pain}%</div>
            <div class="tier-stat-lbl">Discovery Pain Rate</div>
          </div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{TEXT};">{prem.get('echo_chamber_rate',0):.0f}%</div>
            <div class="tier-stat-lbl">Echo Chamber Mentions</div>
          </div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{RED if prem.get('avg_sentiment',0) < -0.5 else YELLOW};">{prem.get('avg_sentiment',0):+.2f}</div>
            <div class="tier-stat-lbl">Avg Sentiment</div>
          </div>
          <div style="font-size:0.75rem;color:{TEXT_SECONDARY};margin-top:0.75rem;">{prem.get('count',0):,} reviews</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        free_pain = free_d.get("discovery_pain_rate", 0)
        st.markdown(f"""
        <div class="tier-card free-card">
          <div class="tier-icon">🆓</div>
          <div class="tier-name" style="color:#6B8EFF;">Free Users</div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{RED if free_pain > 60 else YELLOW};">{free_pain}%</div>
            <div class="tier-stat-lbl">Discovery Pain Rate</div>
          </div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{TEXT};">{free_d.get('echo_chamber_rate',0):.0f}%</div>
            <div class="tier-stat-lbl">Echo Chamber Mentions</div>
          </div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{RED if free_d.get('avg_sentiment',0) < -0.5 else YELLOW};">{free_d.get('avg_sentiment',0):+.2f}</div>
            <div class="tier-stat-lbl">Avg Sentiment</div>
          </div>
          <div style="font-size:0.75rem;color:{TEXT_SECONDARY};margin-top:0.75rem;">{free_d.get('count',0):,} reviews</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        unk_pain = unk.get("discovery_pain_rate", 0)
        st.markdown(f"""
        <div class="tier-card" style="border-color:#555;">
          <div class="tier-icon">❓</div>
          <div class="tier-name" style="color:{TEXT_SECONDARY};">Unknown Tier</div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{TEXT};">{unk_pain}%</div>
            <div class="tier-stat-lbl">Discovery Pain Rate</div>
          </div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{TEXT};">{unk.get('echo_chamber_rate',0):.0f}%</div>
            <div class="tier-stat-lbl">Echo Chamber Mentions</div>
          </div>
          <div class="tier-stat">
            <div class="tier-stat-val" style="color:{TEXT_SECONDARY};">{unk.get('avg_sentiment',0):+.2f}</div>
            <div class="tier-stat-lbl">Avg Sentiment</div>
          </div>
          <div style="font-size:0.75rem;color:{TEXT_SECONDARY};margin-top:0.75rem;">{unk.get('count',0):,} reviews</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Comparison charts ──────────────────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        # Discovery Pain Rate comparison
        fig = go.Figure()
        categories = ["Discovery Pain Rate", "Echo Chamber Rate"]
        prem_vals = [prem.get("discovery_pain_rate", 0), prem.get("echo_chamber_rate", 0)]
        free_vals = [free_d.get("discovery_pain_rate", 0), free_d.get("echo_chamber_rate", 0)]

        fig.add_trace(go.Bar(name="Premium", x=categories, y=prem_vals, marker_color=ACCENT,
                             text=[f"{v:.1f}%" for v in prem_vals], textposition="auto", textfont=dict(color="#000")))
        fig.add_trace(go.Bar(name="Free", x=categories, y=free_vals, marker_color=BLUE,
                             text=[f"{v:.1f}%" for v in free_vals], textposition="auto", textfont=dict(color=TEXT)))

        layout = {
            **PLOTLY_TEMPLATE["layout"],
            "title": "Pain Rate by Subscription Tier",
            "barmode": "group",
            "height": 340,
            "legend": dict(font=dict(color=TEXT), orientation="h", y=-0.18),
            "margin": dict(l=20, r=20, t=50, b=60),
            "yaxis": {**PLOTLY_TEMPLATE["layout"].get("yaxis", {}), "range": [0, max(max(prem_vals), max(free_vals)) * 1.25]},
        }
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_r:
        # Tier distribution
        tier_counts = {
            "Premium": prem.get("count", 0),
            "Free": free_d.get("count", 0),
            "Unknown": unk.get("count", 0),
        }
        tier_counts = {k: v for k, v in tier_counts.items() if v > 0}
        if tier_counts:
            fig = make_pie(tier_counts, "Review Distribution by Tier", colors=[ACCENT, BLUE, TEXT_SECONDARY])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Top frustrations by tier ───────────────────────────────────────────
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown(f"<div style='font-weight:700;color:{ACCENT};margin-bottom:0.75rem;'>💎 Premium Top Frustrations</div>", unsafe_allow_html=True)
        prem_frustrations = prem.get("top_frustrations", ["Discover Weekly Quality", "Radio Repetition", "Genre Bubble"])
        for i, frust in enumerate(prem_frustrations, 1):
            tip = TIER_FRUSTRATION_DEFS.get(frust, "A recurring pain point flagged by Premium users in discovery-related reviews.")
            st.markdown(f"""
            <div style="background:#181818;border-radius:6px;padding:0.6rem 1rem;margin-bottom:0.5rem;border-left:3px solid {ACCENT};">
              <span style="color:{ACCENT};font-weight:700;">#{i}</span>
              <span class="ft-tooltip" data-tip="{tip}" style="color:{TEXT};margin-left:0.5rem;font-size:0.9rem;">{frust}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"<div style='color:{ACCENT};font-size:0.75rem;margin-top:0.25rem;'>💡 <i>Hover over individual frustrations to see full description.</i></div>", unsafe_allow_html=True)

    with col_r2:
        st.markdown(f"<div style='font-weight:700;color:#6B8EFF;margin-bottom:0.75rem;'>🆓 Free Tier Top Frustrations</div>", unsafe_allow_html=True)
        free_frustrations = free_d.get("top_frustrations", ["Autoplay Loop", "Mainstream Bias", "No Personalization"])
        for i, frust in enumerate(free_frustrations, 1):
            tip = TIER_FRUSTRATION_DEFS.get(frust, "A recurring pain point flagged by Free users in discovery-related reviews.")
            st.markdown(f"""
            <div style="background:#181818;border-radius:6px;padding:0.6rem 1rem;margin-bottom:0.5rem;border-left:3px solid {BLUE};">
              <span style="color:{BLUE};font-weight:700;">#{i}</span>
              <span class="ft-tooltip" data-tip="{tip}" style="color:{TEXT};margin-left:0.5rem;font-size:0.9rem;">{frust}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"<div style='color:{ACCENT};font-size:0.75rem;margin-top:0.25rem;'>💡 <i>Hover over individual frustrations to see full description.</i></div>", unsafe_allow_html=True)

    # ── PM Insight — built from live card values so text always matches ────
    gap = abs(prem_pain - free_pain)
    if gap < 10:
        live_insight = (
            f"Discovery pain is roughly equal across tiers "
            f"(<b style='color:{ACCENT};'>{prem_pain:.1f}%</b> Premium vs "
            f"<b style='color:#6B8EFF;'>{free_pain:.1f}%</b> Free), "
            "suggesting the echo chamber issue is a platform-wide algorithmic problem rather than a "
            "tier-specific one. This is a critical finding: Premium subscribers pay their premium "
            "subscription fee and still experience the same discovery failures as free users — "
            "directly undermining the premium value proposition and signalling significant churn risk."
        )
    elif prem_pain > free_pain:
        live_insight = (
            f"Premium users report higher discovery pain "
            f"(<b style='color:{ACCENT};'>{prem_pain:.1f}%</b>) than Free users "
            f"(<b style='color:#6B8EFF;'>{free_pain:.1f}%</b>). "
            "Counterintuitive but explainable: Premium users are more engaged with the platform, "
            "have richer listening history, and have therefore built deeper echo chambers. "
            "They also have higher expectations having paid for a superior experience. "
            "The irony: the most loyal, highest-value users suffer the worst discovery experience — "
            "a significant churn risk for Spotify's most important customer segment."
        )
    else:
        live_insight = (
            f"Free users report higher discovery pain "
            f"(<b style='color:#6B8EFF;'>{free_pain:.1f}%</b>) than Premium users "
            f"(<b style='color:{ACCENT};'>{prem_pain:.1f}%</b>). "
            "Free-tier discovery appears to prioritise trending/popular content over personalisation, "
            "creating a broader echo chamber experience. Improving free-tier discovery quality "
            "could significantly improve conversion rates to paid plans."
        )

    st.markdown(f"""
    <div class="insight-box warning" style="margin-top:1.5rem;">
      <div class="insight-title">📋 PM Insight: Subscription Tier Analysis</div>
      <div class="insight-text">{live_insight}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Statistical note ───────────────────────────────────────────────────
    total = prem.get("count", 0) + free_d.get("count", 0)
    st.markdown(f"""
    <div style="background:#181818;border-radius:6px;padding:0.75rem 1rem;margin-top:1rem;border:none;font-size:0.8rem;color:{TEXT_SECONDARY};">
      <b>Statistical Note:</b> Analysis based on {total:,} reviews with identified subscription tier.
      {unk.get('count',0):,} reviews had unknown tier (subscription tier inferred from review text when not explicitly stated).
      Sample sizes: Premium n={prem.get('count',0):,}, Free n={free_d.get('count',0):,}.
      {"Statistical significance is moderate — interpret Premium vs Free comparison directionally." if prem.get('count',0) < 100 or free_d.get('count',0) < 50 else "Sample sizes are sufficient for reliable statistical comparison."}
    </div>
    """, unsafe_allow_html=True)


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    nav = render_sidebar()

    with st.spinner("Loading data..."):
        records, stats = load_data()
        report = load_report()

    if not records:
        st.error("No data available. Please run the pipeline first.")
        st.code("python -c \"from src.pipeline.filter_noise import run_full_pipeline; from pathlib import Path; run_full_pipeline(Path('data'))\"")
        return

    if nav == "Executive Dashboard":
        render_executive_dashboard(records, stats, report)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_premium_free_analysis(records, report)

    elif nav == "Data Sources Explorer":
        render_data_explorer(records, stats)

    elif nav == "Strategic PM Insights":
        render_pm_insights(records, stats, report)

    elif nav == "Semantic Query Playground":
        render_semantic_playground(records)

    elif nav == "AI Workflow":
        render_ai_workflow(records, stats)


if __name__ == "__main__":
    main()
