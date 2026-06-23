"""
Synthetic review generator — 8,500 rows across 5 sources.

Realistic distribution targets:
  Total ingested:            8,500
  Noise rejected (~24%):    ~2,040
  Used (~76%):              ~6,460
  Discovery pain (of used): ~28-32%   (NOT 100%)
  Premium discovery pain:   ~42%
  Free discovery pain:      ~12%
  Overall pain rate:        ~29%
"""
from __future__ import annotations

import csv
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

random.seed(42)

# ── Word banks for template variation ──────────────────────────────────────

DURATIONS = [
    "2 weeks", "a month", "3 months", "6 months", "almost a year",
    "over a year", "2 years", "3 years", "4 years", "5 years",
    "since 2018", "since 2019", "since 2020", "since 2021", "since launch",
]

TIERS_LABEL = {
    "premium": ["Premium subscriber", "premium user", "paying subscriber",
                "Premium member", "paid user"],
    "free":    ["free user", "free tier user", "non-paying user",
                "free account holder", "on the free plan"],
    "unknown": ["Spotify user", "listener", "long-time user", "daily user"],
}

SENTIMENT_MAP = {
    "discovery_echo":    (-0.82, -0.55),
    "discovery_dw":      (-0.78, -0.50),
    "discovery_radio":   (-0.75, -0.45),
    "discovery_autoplay":(-0.70, -0.40),
    "noise_login":       (-0.55, -0.20),
    "noise_crash":       (-0.65, -0.25),
    "noise_payment":     (-0.60, -0.20),
    "noise_audio":       (-0.50, -0.15),
    "general_positive":  ( 0.35,  0.85),
    "general_negative":  (-0.50, -0.15),
    "ad_complaint":      (-0.60, -0.25),
    "feature_request":   (-0.30,  0.15),
    "playlist_praise":   ( 0.25,  0.70),
}

# ── Template fragments (mixed for variation) ───────────────────────────────

ECHO_OPENERS = [
    "Been a {tier} for {dur}. The algorithm is completely stuck in a loop.",
    "After {dur} of {tier} membership, I'm trapped in a music echo chamber.",
    "I've noticed for {dur} now that Spotify just plays the same music.",
    "Started as a {tier} {dur} ago and my recommendations haven't changed.",
    "As a {tier} for {dur}, the echo chamber problem has become unbearable.",
    "Genuinely shocked at how repetitive Spotify has gotten over {dur}.",
    "I've been paying for {tier} for {dur} and the algorithm is broken.",
    "The recommendation loop has gotten so bad I'm considering canceling.",
    "{dur} of Premium and my taste profile is completely stuck in the past.",
    "Something is deeply wrong with the algorithm. Same music for {dur}.",
]

ECHO_BODIES = [
    "Every playlist Spotify generates for me contains the same 80 songs. I've heard all of them hundreds of times.",
    "The Made For You section never shows me anything I haven't already listened to a thousand times.",
    "No matter what I play, the recommendations snap back to the same 50 songs within days.",
    "My taste profile was locked in 2022 and Spotify refuses to acknowledge that I've moved on.",
    "I explored jazz for a week and now Spotify thinks I only listen to jazz. Can't escape it.",
    "The algorithm punishes curiosity. Every time I try a new genre it takes over my entire recommendation profile.",
    "Discover Weekly, Daily Mix, Artist Radio — all of them cycle through the same content.",
    "I've calculated it: there are roughly 150 songs in total rotation across all my Spotify recommendations.",
    "The collaborative filtering model just keeps reinforcing what I already know. Zero discovery happening.",
    "It feels like the algorithm found my comfort zone in 2022 and has been stuck there ever since.",
    "My gym playlist has contaminated everything. Now ALL recommendations are high-energy even when I want something calm.",
    "Podcast listening has completely wrecked my music recommendations. The algorithm can't separate them.",
    "I listen to background music 8 hours a day for work. Now 100% of recommendations are ambient/lo-fi.",
    "The algorithm learned from my most-played songs, not my most-loved songs. Big difference.",
    "I've been in the same sonic bubble for 18 months. Genuinely cannot remember the last new discovery.",
]

ECHO_CLOSERS = [
    "Genuinely considering switching to Apple Music for the discovery features.",
    "YouTube recommends me more new music than Spotify's dedicated discovery tools.",
    "The promise of personalized discovery is simply not being delivered.",
    "This is the biggest reason I'm thinking about cancelling my subscription.",
    "Bandcamp does a better job of showing me new music and it doesn't even have my listening history.",
    "I have 100 million songs available and Spotify serves me the same 200. That's a product failure.",
    "Would pay extra for an actual exploration feature that doesn't contaminate my recommendations.",
    "Please let me reset my taste profile. That's all I'm asking.",
    "I found more new artists in one week on Tidal than in two years on Spotify.",
    "The algorithm needs a novelty setting. Give users control over how conservative it is.",
]

DW_OPENERS = [
    "Discover Weekly used to be the best feature in music tech. Now it's useless.",
    "My Discover Weekly this week had {n} songs I already had in my library.",
    "Opened Discover Weekly and found songs I explicitly saved months ago. That's not discovery.",
    "I track my Discover Weekly every Monday. Quality has dropped significantly this year.",
    "Discover Weekly was revolutionary in 2015. In 2024 it just reshuffles my existing library.",
    "Three Discover Weekly songs this week were from artists I already follow. That defeats the purpose.",
    "I've given up on Discover Weekly. It stopped discovering anything new about 18 months ago.",
    "Discover Weekly sent me songs I had already liked and then unliked. How does that happen?",
]

DW_BODIES = [
    "The feature is supposed to find music I've never heard. It consistently fails at the core promise.",
    "At least 40% of each playlist is music I already know well. That's not acceptable for a 'discovery' feature.",
    "The algorithm has gotten so confident in my taste that it stopped taking any risks at all.",
    "Songs I've played hundreds of times keep appearing. There's no quality gate checking existing library.",
    "I remember when Discover Weekly found me Fleet Foxes, Bon Iver, and dozens of artists I now love. That magic is gone.",
    "It feels like the playlist is generated by sampling my existing library rather than exploring beyond it.",
    "The songs are fine but they're just reconfirmations of taste I already have, not expansions of it.",
    "Two consecutive weeks had 70% song overlap. That's barely a shuffle, let alone discovery.",
]

DW_CLOSERS = [
    "Please implement a basic check: don't recommend songs already in a user's library.",
    "The feature needs a minimum novelty threshold before it can be called 'Discover' anything.",
    "I'd rather have an 'honest shuffle' label than a misleading 'Discover Weekly' that doesn't discover.",
    "Release Radar still works great. Someone needs to apply that same rigor to Discover Weekly.",
]

RADIO_OPENERS = [
    "Artist Radio has become a complete joke. It plays the same {n} songs every session.",
    "I timed it: Artist Radio exhausted all its unique songs in {n} minutes and started repeating.",
    "Radio on Spotify means: play these 40 songs in a slightly different order each time.",
    "Started a radio station for {artist}. Heard the same songs for the 50th time.",
    "The radio feature has never actually introduced me to a song I hadn't heard before.",
    "Why is radio even a feature if it just replays content I already know?",
]

RADIO_BODIES = [
    "Real radio broadcasts new music to listeners. Spotify Radio just automates a fixed playlist.",
    "I counted 47 unique songs across 4 hours of radio. Out of 100 million available. Embarrassing.",
    "The radio pool for any artist seems to be about 40-60 songs total regardless of how long you listen.",
    "It cycles through the same content so predictably I can anticipate the next song.",
    "The feature description says 'explore music similar to what you love' but the pool never expands.",
    "Every artist's radio eventually converges to the same 30 mainstream songs regardless of the seed artist.",
]

RADIO_CLOSERS = [
    "Real radio works because it exposes you to the unknown. Spotify Radio does the opposite.",
    "Please expand the radio pool or admit the feature is just a shuffle of your top artists.",
    "I can recreate the radio experience by just pressing shuffle on my existing library.",
]

AUTOPLAY_OPENERS = [
    "After any playlist ends, autoplay takes over and plays the exact same songs every time.",
    "Autoplay is hardcoded to about 20 songs. Doesn't matter what playlist preceded it.",
    "After 2 years, I've memorized Spotify's autoplay queue. That's how predictable it is.",
    "Why does autoplay always go to the same songs regardless of what I was just listening to?",
    "The autoplay algorithm seems completely disconnected from the playlist that just ended.",
]

AUTOPLAY_BODIES = [
    "The autoplay pool seems to be about 50 songs total and it picks 20 of them each session.",
    "Context-blind autoplay is the definition of the problem: it doesn't know WHY I was listening to what I was.",
    "My sleep playlist ends and autoplay starts playing upbeat pop. The algorithm has no contextual awareness.",
    "Autoplay after a jazz playlist = pop hits. After metal = pop hits. After ambient = pop hits. Always pop hits.",
]

AUTOPLAY_CLOSERS = [
    "Autoplay should extend the mood and context of the previous playlist, not start fresh with its defaults.",
    "The feature would be great if it had any awareness of what came before it.",
]

# ── Noise templates ────────────────────────────────────────────────────────

LOGIN_TEMPLATES = [
    "Can't log into my account. Password reset isn't working. Terrible customer support.",
    "Logged out of all my devices randomly and now the app won't let me back in.",
    "Two-factor authentication broke after the last update. Can't access my account for 3 days.",
    "My account was hacked and Spotify support has been completely useless in recovering it.",
    "Login keeps failing with error code 409. Cleared cache, reinstalled, nothing works.",
    "Suddenly can't log in on my phone. Works on desktop but mobile is completely broken.",
    "Password reset emails not arriving. Tried 10 times. No email. App is locked.",
    "Got logged out mid-playlist and can't get back in. This happens every few weeks.",
    "Family plan login stopped working for all members simultaneously. Support ticket ignored for 4 days.",
    "Can't log in after updating the app. Error code keeps appearing. Frustrated.",
]

CRASH_TEMPLATES = [
    "App crashes every time I try to download a playlist for offline listening. Unusable.",
    "Spotify crashes immediately when I try to open it after the latest update. Please fix.",
    "The app freezes for 30 seconds every time I switch songs. Makes it completely unusable.",
    "Random crashes during playback. Lost my queue twice today. Very frustrating.",
    "Widgets on my home screen keep crashing the app. iOS 17 compatibility is broken.",
    "App crashes when I try to share songs. Social features completely broken.",
    "Car mode crashes every time I unlock my phone. Can't use Spotify while driving safely.",
    "Crossfade feature causes the app to crash. Turned it off as a workaround but I want it.",
    "The equalizer settings crash the app every time I open them. Reinstalled, same issue.",
    "App won't load past the splash screen. Tried on 3 different devices. Same problem.",
    "Bluetooth connection keeps dropping and app crashes when it reconnects. Bug in latest version.",
    "Memory leak causing the app to use 2GB RAM and then crash after 30 minutes.",
]

PAYMENT_TEMPLATES = [
    "Charged twice this month. Contacted support 2 weeks ago and still no refund.",
    "Student discount expired without warning and I was charged full price without consent.",
    "Family plan billing is completely broken. Two family members got charged individually.",
    "Tried to cancel my subscription but the app keeps charging me anyway. Escalating to bank.",
    "Promo price ended and I wasn't notified. Suddenly charged €9.99 instead of €4.99.",
    "Gift card applied to account but subscription still charging my credit card. Double billing.",
    "Wrong currency being charged. Set up in EUR, being charged in USD at bad exchange rate.",
    "Annual plan auto-renewed without the promised email reminder. Want a refund.",
    "Discount code not applying at checkout despite being advertised as valid.",
    "Cancelled Premium but still being charged monthly. Three months of unauthorized charges.",
]

AUDIO_TEMPLATES = [
    "Audio quality dropped significantly after the last update. Everything sounds muffled.",
    "Bluetooth headphones always connect at low quality instead of high quality. Settings ignored.",
    "Lyrics feature not working for most songs. Just shows generic placeholder text.",
    "Songs randomly play at half volume. Volume normalization is broken.",
    "Offline downloads keep corrupting and need to be re-downloaded weekly.",
    "Podcast audio is much louder than music tracks. Volume leveling doesn't work.",
    "Gapless playback isn't actually gapless anymore. Annoying pause between tracks.",
    "Audio drops out for 2-3 seconds every hour. Happens across all devices and networks.",
    "EQ settings reset to default every time I close and reopen the app.",
]

# ── General (non-discovery, non-noise) templates ───────────────────────────

POSITIVE_TEMPLATES = [
    "Honestly love Spotify. The catalog is massive and I can find almost anything I want.",
    "The interface is clean and intuitive. Premium is 100% worth it for ad-free listening.",
    "Collaborative playlists with friends have been such a fun feature. Really enjoying it.",
    "Sound quality is excellent with the high quality setting. Worth every penny.",
    "The app works perfectly across all my devices. Seamless switching is a killer feature.",
    "Liked Songs organization is excellent. My library of 3,000 songs is totally manageable.",
    "Spotify's catalog depth for niche genres is unmatched. Found albums I couldn't find anywhere else.",
    "Blend feature with my partner is honestly adorable and makes surprisingly good playlists.",
    "Offline mode works flawlessly. Downloaded 200 albums for my camping trip, perfect.",
    "The UI updates have been consistently good. Very well designed product overall.",
    "Artist pages are comprehensive. Love seeing concert dates, discography, and related artists.",
    "Podcasts and music in one app is genuinely convenient. Would hate to go back to separate apps.",
    "Wrapped every year is such a fun tradition. Gets me excited to see my listening habits.",
    "Customer support actually resolved my issue in 24 hours. Impressed.",
    "The search functionality is excellent. Can find any song by lyrics, artist, or mood.",
    "Sharing playlists with family across the family plan works perfectly. Great value.",
    "The AI DJ feature is surprisingly good. Actually plays music I enjoy without me having to curate.",
    "Audiobooks integration is a welcome addition. Nice to have everything in one place.",
    "The social features — seeing what friends listen to — genuinely influencing my taste in good ways.",
    "Queue management is excellent. Easy to add, reorder, and manage upcoming tracks.",
]

GENERAL_NEG_TEMPLATES = [
    "The home screen recommendations are way too focused on popular music. More variety please.",
    "Please add a proper sleep timer. The workarounds are clunky.",
    "The Like button should be easier to undo. I accidentally liked things I didn't mean to.",
    "Podcast playlist management is confusing. Hard to organize episodes across different shows.",
    "Library sorting options are too limited. I want to sort by date added, not just alphabetically.",
    "The desktop app feels neglected compared to mobile. Basic features are missing.",
    "Mini player controls on iOS lock screen don't always work properly.",
    "Shuffle algorithm is not truly random. Keeps playing the same songs even in shuffle mode.",
    "The search results prioritize popular versions over original recordings too often.",
    "Album release date sorting would be a great addition. Currently can't browse by year easily.",
    "The Recently Played list doesn't go back far enough. Only shows last 50 items.",
    "Group session feature keeps dropping members randomly. Needs stability improvement.",
    "Handling of classical music is poor. Composer and performer tags are all over the place.",
    "The 'Hide Song' feature should be more prominent. Hard to find in the menu.",
    "Listening history should be more detailed. I want to see full play logs, not just recent.",
]

AD_COMPLAINT_TEMPLATES = [
    "The ads on free tier are getting more aggressive. 3 ads after every 2 songs now.",
    "Ad volume is significantly louder than the music. Jarring and annoying.",
    "The same ad has played 40 times today. Ad frequency capping is completely broken.",
    "Video ads are way too long for a music app. 30-second video ads for every break.",
    "Ad targeting is completely off. Getting ads for things completely irrelevant to me.",
    "Free tier shuffle restrictions make it nearly impossible to listen to what I want.",
    "Can't skip on free? I've heard this song 3 times today from a playlist I don't even like.",
    "The free version has become so restricted it's barely usable. Almost a paywall demo.",
    "Six ads in a row during a commute. Considering a competitor with a better free tier.",
    "Ads interrupt podcast playback in weird places. Mid-sentence ad breaks are terrible UX.",
    "I understand ads but the frequency on free has tripled in the past year. Feels predatory.",
    "Free tier feels deliberately broken to force upgrades. Shuffle limits are artificial constraints.",
]

PLAYLIST_TEMPLATES = [
    "The collaborative playlist feature with my band members has been fantastic for planning setlists.",
    "Smart shuffle on playlists is actually quite good. Keeps things fresh without losing the playlist's character.",
    "Wish I could sort playlist by BPM or key for DJ purposes. Missing feature for power users.",
    "The playlist merge feature would save me so much time. Currently have to manually combine.",
    "Folder organization for playlists is still missing. 200 playlists with no hierarchy is chaos.",
    "The 'Add to playlist' search within the dialog is too slow. Needs optimization.",
    "Collaborative playlists need admin controls. Anyone can delete songs currently.",
    "Playlist covers should be customizable with more template options. Current options are limited.",
    "Being able to see who added which song in a collaborative playlist is great for avoiding duplicates.",
    "The recommended songs at the bottom of playlists is a genuinely useful feature. Often good.",
]

FEATURE_TEMPLATES = [
    "Would love a proper equalizer with more bands. Current EQ is too basic for audiophiles.",
    "Please add lossless audio for Premium subscribers. Every competitor offers it now.",
    "An offline queue that's separate from downloads would be incredibly useful.",
    "The 'Your Library' tab needs better organization. Mixing podcasts with music is confusing.",
    "Dark mode customization would be a great addition. Love the default but want more themes.",
    "Please add lyrics to more international songs. The coverage outside English is poor.",
    "A 'date added' filter for albums would help me find new additions to my library easily.",
    "The 'You might also like' section on artist pages is genuinely useful. Keep improving it.",
    "Wish there was a way to import playlists from Apple Music more easily. Migration is painful.",
    "A 'revisit this artist' feature for artists I used to love but haven't heard in years would be great.",
]

ARTISTS_SUBREDDITS = [
    "r/spotify", "r/spotifymusic", "r/Music", "r/LetsTalkMusic",
    "r/indieheads", "r/hiphopheads", "r/electronicmusic",
    "r/classicalmusic", "r/metal", "r/popheads", "r/jazz",
]

YT_CHANNELS = [
    "Music Tech Reviews", "StreamingComparison", "TechExplained",
    "MusicExperiments", "AppTestingPro", "MusicDiscoveryChannel",
    "DigitalLifestyle", "StreamingCritique", "DataDrivenMusic",
    "GenZInsights", "TechBusinessAnalysis", "MusicMemory",
    "HonestStreamingReview", "AlgorithmCritique", "AudiophileReview",
]

FORUM_CATEGORIES = [
    "Music & Discovery", "Content Questions", "Premium Features",
    "App Performance", "Recommendations & Playlists",
]

ARTISTS_SEED = [
    "Radiohead", "Taylor Swift", "The Weeknd", "Billie Eilish",
    "Led Zeppelin", "Miles Davis", "Kendrick Lamar", "Arctic Monkeys",
    "Fleetwood Mac", "Frank Ocean", "Bon Iver", "Doja Cat",
    "Pink Floyd", "Bad Bunny", "Olivia Rodrigo", "Tyler the Creator",
]


# ── Row builders ───────────────────────────────────────────────────────────

def _rand_date(days_back: int = 540) -> str:
    base = datetime(2025, 1, 1)
    delta = timedelta(days=random.randint(0, days_back))
    return (base - delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rand_sentiment(category: str) -> float:
    lo, hi = SENTIMENT_MAP.get(category, (-0.3, 0.3))
    return round(random.uniform(lo, hi), 3)


_SEGMENT_WEIGHTS: dict = {
    "discovery_echo":     [("Loyal Long-Timer", 35), ("Genre Explorer", 35), ("Power Curator", 20), ("Passive Radio Listener", 10)],
    "discovery_dw":       [("Loyal Long-Timer", 35), ("Genre Explorer", 30), ("Power Curator", 20), ("Passive Radio Listener", 15)],
    "discovery_radio":    [("Passive Radio Listener", 40), ("Loyal Long-Timer", 25), ("Power Curator", 20), ("Genre Explorer", 15)],
    "discovery_autoplay": [("Passive Radio Listener", 35), ("Loyal Long-Timer", 25), ("Power Curator", 20), ("Genre Explorer", 20)],
    "general_positive":   [("General Listener", 30), ("Loyal Long-Timer", 20), ("Passive Radio Listener", 20), ("Power Curator", 15), ("Genre Explorer", 15)],
    "general_negative":   [("General Listener", 25), ("Genre Explorer", 20), ("Loyal Long-Timer", 20), ("Power Curator", 20), ("Free Tier Casual", 15)],
    "ad_complaint":       [("Free Tier Casual", 60), ("General Listener", 20), ("Passive Radio Listener", 15), ("Power Curator", 5)],
    "playlist_praise":    [("Power Curator", 30), ("General Listener", 25), ("Loyal Long-Timer", 20), ("Genre Explorer", 15), ("Passive Radio Listener", 10)],
    "feature_request":    [("General Listener", 25), ("Power Curator", 25), ("Genre Explorer", 20), ("Loyal Long-Timer", 15), ("Passive Radio Listener", 15)],
    "noise_login":        [("General Listener", 60), ("Passive Radio Listener", 20), ("Power Curator", 10), ("Free Tier Casual", 10)],
    "noise_crash":        [("General Listener", 60), ("Passive Radio Listener", 20), ("Power Curator", 10), ("Free Tier Casual", 10)],
    "noise_payment":      [("General Listener", 50), ("Free Tier Casual", 30), ("Loyal Long-Timer", 20)],
    "noise_audio":        [("General Listener", 50), ("Power Curator", 25), ("Passive Radio Listener", 25)],
}


def _segment_for_category(cat_key: str) -> str:
    weights_list = _SEGMENT_WEIGHTS.get(cat_key, [("General Listener", 100)])
    segments = [s for s, _ in weights_list]
    weights = [w for _, w in weights_list]
    return random.choices(segments, weights=weights, k=1)[0]


def _tier_weighted(premium_w=0.60, free_w=0.35) -> str:
    r = random.random()
    if r < premium_w:
        return "premium"
    elif r < premium_w + free_w:
        return "free"
    return "unknown"


def _tier_for_category(category: str) -> str:
    if "discovery" in category or "echo" in category or "dw" in category or "radio" in category or "autoplay" in category:
        # Discovery complaints: 70% premium, 25% free
        return _tier_weighted(0.70, 0.25)
    elif "ad_complaint" in category:
        # Ad complaints: 90% free
        return _tier_weighted(0.08, 0.90)
    elif "noise" in category:
        # Noise: mixed
        return _tier_weighted(0.55, 0.38)
    else:
        return _tier_weighted(0.60, 0.35)


def _build_discovery_text(category: str) -> str:
    n_songs = random.choice([20, 30, 40, 50, "the same"])
    artist = random.choice(ARTISTS_SEED)
    n_min = random.choice([60, 90, 120, "about 90"])

    if "echo" in category:
        opener = random.choice(ECHO_OPENERS).format(
            tier=random.choice(["Premium", "Spotify Premium"]),
            dur=random.choice(DURATIONS), n=n_songs, artist=artist,
        )
        body = random.choice(ECHO_BODIES)
        closer = random.choice(ECHO_CLOSERS)
    elif "dw" in category:
        opener = random.choice(DW_OPENERS).format(n=random.randint(3, 10), artist=artist)
        body = random.choice(DW_BODIES)
        closer = random.choice(DW_CLOSERS)
    elif "radio" in category:
        opener = random.choice(RADIO_OPENERS).format(n=n_songs, artist=artist, min=n_min)
        body = random.choice(RADIO_BODIES)
        closer = random.choice(RADIO_CLOSERS)
    else:  # autoplay
        opener = random.choice(AUTOPLAY_OPENERS)
        body = random.choice(AUTOPLAY_BODIES)
        closer = random.choice(AUTOPLAY_CLOSERS)

    parts = [opener, body]
    if random.random() > 0.3:
        parts.append(closer)
    return " ".join(parts)


def _build_text(category: str) -> str:
    if "discovery" in category:
        return _build_discovery_text(category)
    elif category == "noise_login":
        return random.choice(LOGIN_TEMPLATES)
    elif category == "noise_crash":
        return random.choice(CRASH_TEMPLATES)
    elif category == "noise_payment":
        return random.choice(PAYMENT_TEMPLATES)
    elif category == "noise_audio":
        return random.choice(AUDIO_TEMPLATES)
    elif category == "general_positive":
        return random.choice(POSITIVE_TEMPLATES)
    elif category == "general_negative":
        return random.choice(GENERAL_NEG_TEMPLATES)
    elif category == "ad_complaint":
        return random.choice(AD_COMPLAINT_TEMPLATES)
    elif category == "playlist_praise":
        return random.choice(PLAYLIST_TEMPLATES)
    else:
        return random.choice(FEATURE_TEMPLATES)


def _source_metadata(source: str, i: int) -> dict:
    meta = {}
    if source == "reddit":
        meta["subreddit"] = random.choice(ARTISTS_SUBREDDITS)
        meta["score"] = random.randint(1, 3500)
        meta["num_comments"] = random.randint(0, 900)
    elif source == "youtube":
        meta["channel"] = random.choice(YT_CHANNELS)
        meta["video_id"] = f"yt_vid_{i:05d}"
        meta["likes"] = random.randint(0, 8000)
    elif source == "spotify_community":
        meta["category"] = random.choice(FORUM_CATEGORIES)
        meta["likes"] = random.randint(0, 4500)
        meta["replies"] = random.randint(0, 1200)
    elif source in ("play_store", "app_store"):
        meta["rating"] = random.choices([1, 2, 3, 4, 5], weights=[25, 30, 20, 15, 10])[0]
        meta["helpful_count"] = random.randint(0, 2500)
    return meta


# ── Category plan ──────────────────────────────────────────────────────────
# Targets: 8,500 total
#   Noise   (~24%): 2,040
#   Signal  (~76%): 6,460
#     Of signal, ~29% = discovery complaint → 1,875
#     Rest 71%       → general/positive/ads   4,585

CATEGORY_PLAN = [
    # (category_key,          count, is_noise, is_discovery)
    # ── Discovery complaints (22% of total)
    ("discovery_echo",        935,  False, True),
    ("discovery_dw",          510,  False, True),
    ("discovery_radio",       255,  False, True),
    ("discovery_autoplay",    170,  False, True),
    # ── Noise (24%)
    ("noise_crash",           680,  True,  False),
    ("noise_login",           595,  True,  False),
    ("noise_payment",         425,  True,  False),
    ("noise_audio",           340,  True,  False),
    # ── General signal (54%)
    ("general_positive",     1870,  False, False),
    ("general_negative",      935,  False, False),
    ("ad_complaint",          850,  False, False),
    ("playlist_praise",       680,  False, False),
    ("feature_request",       255,  False, False),
]

SOURCE_WEIGHTS = {
    "reddit":            0.30,
    "youtube":           0.25,
    "spotify_community": 0.20,
    "play_store":        0.15,
    "app_store":         0.10,
}

SOURCES = list(SOURCE_WEIGHTS.keys())
SOURCE_PROBS = list(SOURCE_WEIGHTS.values())


# ── Main generator ─────────────────────────────────────────────────────────

def generate_dataset(n_rows: int = 8500, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).parent.parent / "data" / "raw" / "all_reviews.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build category pool matching exact counts
    pool: list[tuple[str, bool, bool]] = []
    for cat_key, count, is_noise, is_discovery in CATEGORY_PLAN:
        pool.extend([(cat_key, is_noise, is_discovery)] * count)

    # Trim or pad to n_rows
    while len(pool) < n_rows:
        pool.extend(pool[:n_rows - len(pool)])
    pool = pool[:n_rows]
    random.shuffle(pool)

    fieldnames = [
        "id", "source", "subreddit", "category", "channel", "video_id",
        "author", "title", "body", "rating", "score", "likes", "helpful_count",
        "replies", "num_comments", "created_at", "url",
        "subscription_tier", "sentiment_raw",
        "_category_key", "_is_noise", "_is_discovery", "_user_segment",
    ]

    rows_written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for i, (cat_key, is_noise, is_discovery) in enumerate(pool):
            source = random.choices(SOURCES, weights=SOURCE_PROBS)[0]
            tier = _tier_for_category(cat_key)
            text = _build_text(cat_key)
            sentiment = _rand_sentiment(cat_key)
            segment = _segment_for_category(cat_key)

            # Leave title empty — body is the full review text.
            # Populating title from body causes verbatim_quote duplication because
            # load_csv_raw concatenates title+body into the text field.

            row: dict = {
                "id": f"syn_{i:06d}",
                "source": source,
                "subreddit": "",
                "category": "",
                "channel": "",
                "video_id": "",
                "author": f"user_{random.randint(10000, 99999)}",
                "title": "",
                "body": text,
                "rating": None,
                "score": 0,
                "likes": 0,
                "helpful_count": 0,
                "replies": 0,
                "num_comments": 0,
                "created_at": _rand_date(),
                "url": "",
                "subscription_tier": tier,
                "sentiment_raw": sentiment,
                "_category_key": cat_key,
                "_is_noise": is_noise,
                "_is_discovery": is_discovery,
                "_user_segment": segment,
            }
            row.update(_source_metadata(source, i))
            writer.writerow(row)
            rows_written += 1

    logger.info("Generated %d synthetic rows → %s", rows_written, output_path)

    # Verify distribution
    noise_count = sum(1 for _, is_noise, _ in pool if is_noise)
    disc_count = sum(1 for _, _, is_disc in pool if is_disc)
    logger.info(
        "Distribution: noise=%d (%.1f%%), discovery=%d (%.1f%%)",
        noise_count, noise_count / n_rows * 100,
        disc_count, disc_count / n_rows * 100,
    )

    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    path = generate_dataset()
    print(f"\nDataset written to: {path}")
