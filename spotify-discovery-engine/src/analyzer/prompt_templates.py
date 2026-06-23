"""
LLM prompt templates for Spotify discovery analysis.
Maps qualitative feedback to structured JSON schema for PM insights.
"""

SYSTEM_PROMPT = """You are a Senior Product Manager and UX Researcher at Spotify.
Your task is to analyze user reviews about music discovery issues and extract structured insights.
Always respond with valid JSON only — no markdown, no explanations outside the JSON structure."""


SINGLE_REVIEW_ANALYSIS_PROMPT = """Analyze this user review about Spotify's music discovery experience:

REVIEW:
{review_text}

SOURCE: {source}
SUBSCRIPTION TIER: {tier}
RATING: {rating}

Extract and return a JSON object with EXACTLY this structure:
{{
  "behavioral_root_cause": "<one of: Feedback Loop Bias | Passive Fatigue | Contextual Over-reliance | Genre Bubble | Taste Evolution Lag | Niche Content Gap | Cold Start Anchoring | General Discovery Frustration>",
  "interaction_frustration": "<specific UX failure point where discovery intent breaks>",
  "implied_user_segment": "<one of: Passive Radio Listener | Power Curator | Genre Explorer | Loyal Long-Timer | Free Tier Casual | General Listener>",
  "key_verbatim_quote": "<the single most compelling sentence from the review that would resonate in a PM presentation>",
  "sentiment_score": <float between -1.0 (very negative) and 1.0 (very positive)>,
  "echo_chamber_severity": "<Low | Medium | High | Critical>",
  "discovery_feature_mentioned": "<Discover Weekly | Artist Radio | Daily Mix | Autoplay | Made For You | Release Radar | Multiple | None>",
  "actionable_pm_insight": "<one concrete product change Spotify could make to address this specific complaint>"
}}"""


BATCH_SYNTHESIS_PROMPT = """You have {n} user reviews about Spotify's music discovery problems.

REVIEWS (JSON array):
{reviews_json}

Create a strategic PM synthesis report as a JSON object with this structure:
{{
  "executive_summary": "<2-3 sentence summary of the core discovery problem pattern>",
  "top_3_pain_points": [
    {{"pain_point": "<name>", "prevalence_pct": <number>, "description": "<brief>"}},
    {{"pain_point": "<name>", "prevalence_pct": <number>, "description": "<brief>"}},
    {{"pain_point": "<name>", "prevalence_pct": <number>, "description": "<brief>"}}
  ],
  "user_segment_breakdown": {{
    "Passive Radio Listener": {{"pct": <number>, "top_complaint": "<brief>"}},
    "Power Curator": {{"pct": <number>, "top_complaint": "<brief>"}},
    "Genre Explorer": {{"pct": <number>, "top_complaint": "<brief>"}},
    "Loyal Long-Timer": {{"pct": <number>, "top_complaint": "<brief>"}},
    "Free Tier Casual": {{"pct": <number>, "top_complaint": "<brief>"}}
  }},
  "premium_vs_free_insight": "<PM analysis of whether discovery issues hit premium or free users harder and why>",
  "algorithmic_root_cause_hypothesis": "<technical hypothesis about WHY the echo chamber forms based on user evidence>",
  "top_5_product_recommendations": [
    "<recommendation 1>",
    "<recommendation 2>",
    "<recommendation 3>",
    "<recommendation 4>",
    "<recommendation 5>"
  ],
  "churn_risk_level": "<Low | Medium | High | Critical>",
  "competitive_threat": "<which competitor benefits most from this weakness and how>"
}}"""


SEMANTIC_QUERY_PROMPT = """You are searching through {n} Spotify user reviews to answer a specific question.

QUESTION: {question}

RELEVANT REVIEWS (JSON array):
{reviews_json}

Answer the question by:
1. Identifying the most relevant reviews
2. Synthesizing what they collectively say

Return a JSON object:
{{
  "direct_answer": "<clear, direct answer to the question in 2-3 sentences>",
  "supporting_evidence": [
    {{"quote": "<verbatim excerpt>", "source": "<reddit|spotify_community|etc>", "relevance": "<why this supports the answer>"}},
    {{"quote": "<verbatim excerpt>", "source": "<reddit|spotify_community|etc>", "relevance": "<why this supports the answer>"}},
    {{"quote": "<verbatim excerpt>", "source": "<reddit|spotify_community|etc>", "relevance": "<why this supports the answer>"}}
  ],
  "confidence_level": "<Low | Medium | High>",
  "sample_size": {n},
  "nuance": "<any important caveats or contradicting evidence>"
}}"""


PREMIUM_FREE_ANALYSIS_PROMPT = """Analyze these {n} user reviews to understand the difference in discovery experience between Premium and Free Spotify users.

REVIEWS:
{reviews_json}

Return a JSON object:
{{
  "premium_discovery_pain_rate": <percentage of premium reviews expressing discovery frustration>,
  "free_discovery_pain_rate": <percentage of free reviews expressing discovery frustration>,
  "echo_chamber_premium_pct": <percentage of echo chamber mentions from premium users>,
  "echo_chamber_free_pct": <percentage of echo chamber mentions from free users>,
  "premium_top_frustrations": ["<frustration 1>", "<frustration 2>", "<frustration 3>"],
  "free_top_frustrations": ["<frustration 1>", "<frustration 2>", "<frustration 3>"],
  "who_suffers_more": "<Premium | Free | Equal>",
  "why": "<2-3 sentence PM explanation of the disparity or equality>",
  "business_implication": "<what this means for Spotify's premium value proposition>",
  "recommendation": "<concrete product strategy to address the tier-specific pain>",
  "statistical_note": "<note about sample size and confidence>"
}}"""


PM_INSIGHT_SLIDES_PROMPT = """Create a 10-point executive PM presentation outline based on these Spotify discovery user insights.

KEY DATA:
- Total reviews analyzed: {total_reviews}
- Echo chamber complaint rate: {echo_rate}%
- Discover Weekly dissatisfaction: {dw_rate}%
- Average sentiment score: {avg_sentiment}
- Top user segments: {top_segments}

Return a JSON array of 10 slide objects:
[
  {{
    "slide_number": 1,
    "title": "<slide title>",
    "headline_stat": "<the most impactful number or fact for this slide>",
    "key_message": "<the single most important takeaway>",
    "supporting_points": ["<point 1>", "<point 2>", "<point 3>"],
    "visual_recommendation": "<what chart/visual would work best here>"
  }},
  ...
]"""


def format_single_review_prompt(review: dict) -> str:
    text = review.get("text", review.get("body", review.get("comment", "")))
    return SINGLE_REVIEW_ANALYSIS_PROMPT.format(
        review_text=text[:1500],
        source=review.get("source", "unknown"),
        tier=review.get("subscription_tier", "unknown"),
        rating=review.get("rating", "N/A"),
    )


def format_batch_synthesis_prompt(reviews: list[dict], max_chars: int = 12000) -> str:
    import json as _json

    trimmed = []
    chars = 0
    for r in reviews:
        snippet = {
            "source": r.get("source"),
            "tier": r.get("subscription_tier"),
            "text": r.get("text", r.get("body", r.get("comment", "")))[:300],
            "sentiment": r.get("sentiment_score"),
        }
        snippet_str = _json.dumps(snippet)
        if chars + len(snippet_str) > max_chars:
            break
        trimmed.append(snippet)
        chars += len(snippet_str)

    return BATCH_SYNTHESIS_PROMPT.format(
        n=len(trimmed),
        reviews_json=_json.dumps(trimmed, indent=2),
    )


def format_semantic_query_prompt(question: str, reviews: list[dict], max_reviews: int = 20) -> str:
    import json as _json

    relevant = []
    question_lower = question.lower()
    keywords = question_lower.split()

    for r in reviews:
        text = r.get("text", r.get("body", r.get("comment", ""))).lower()
        score = sum(1 for kw in keywords if kw in text and len(kw) > 3)
        if score > 0:
            relevant.append((score, r))

    relevant.sort(reverse=True)
    top = [r for _, r in relevant[:max_reviews]]

    snippets = [
        {
            "source": r.get("source"),
            "tier": r.get("subscription_tier"),
            "quote": r.get("text", "")[:400],
        }
        for r in top
    ]

    return SEMANTIC_QUERY_PROMPT.format(
        n=len(snippets),
        question=question,
        reviews_json=_json.dumps(snippets, indent=2),
    )


def format_premium_free_prompt(reviews: list[dict]) -> str:
    import json as _json

    snippets = [
        {
            "tier": r.get("subscription_tier"),
            "source": r.get("source"),
            "echo_mention": r.get("is_echo_chamber_mention", False),
            "dw_complaint": r.get("is_discover_weekly_complaint", False),
            "sentiment": r.get("sentiment_score"),
            "text": r.get("text", "")[:200],
        }
        for r in reviews
    ]

    return PREMIUM_FREE_ANALYSIS_PROMPT.format(
        n=len(snippets),
        reviews_json=_json.dumps(snippets[:50], indent=2),
    )
