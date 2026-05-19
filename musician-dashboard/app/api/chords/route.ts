import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

// ─── curl-based fetch (bypasses Cloudflare TLS fingerprint checks) ────────────
// Node's fetch / undici is blocked by UG's Cloudflare config because its TLS
// ClientHello fingerprint looks like a bot.  System curl (Schannel on Windows,
// OpenSSL on Linux) presents a different, whitelisted fingerprint.

const CURL = process.platform === 'win32' ? 'curl.exe' : 'curl';
const UG_HEADERS = [
  '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  '-H', 'Accept-Language: en-US,en;q=0.9',
  '-H', 'Referer: https://www.ultimate-guitar.com/',
];

async function curlFetch(url: string, extraArgs: string[] = []): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync(
      CURL,
      ['--silent', '--max-time', '15', '--compressed', '-L', ...UG_HEADERS, ...extraArgs, url],
      { maxBuffer: 15 * 1024 * 1024 }
    );
    return stdout || null;
  } catch (err) {
    console.error('[curl] Error fetching', url, (err as Error).message?.slice(0, 120));
    return null;
  }
}

// ─── shared fetch ─────────────────────────────────────────────────────────────

async function fetchHtml(url: string, extra: Record<string, string> = {}): Promise<string | null> {
  try {
    const res = await fetch(url, {
      signal: AbortSignal.timeout(10000),
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        ...extra,
      },
    });
    if (!res.ok) { console.log(`[chords] ${url} → HTTP ${res.status}`); return null; }
    return res.text();
  } catch (err) {
    console.error(`[chords] Fetch error ${url}:`, (err as Error).message);
    return null;
  }
}

// ─── __NEXT_DATA__ extractor ──────────────────────────────────────────────────
// CifraClub is a Next.js app — every SSR page embeds all data in a JSON blob.
// This is far more reliable than CSS-selector scraping.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractNextData(html: string): any | null {
  const m = html.match(/<script[^>]+id="__NEXT_DATA__"[^>]*>([\s\S]+?)<\/script>/);
  if (!m) return null;
  try { return JSON.parse(m[1]); } catch { return null; }
}

// CifraClub ProSheet format uses {t:Am} for chords, {c:section}, {eot}/{sot}
function convertProSheet(raw: string): string {
  return raw
    .replace(/\{t:([^}]+)\}/g, '$1')   // {t:Am} → Am
    .replace(/\{c:([^}]+)\}/g, '[$1]') // {c:Verse} → [Verse]
    .replace(/\{[^}]*\}/g, '')          // remove any other {markers}
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// ─── slug helper ──────────────────────────────────────────────────────────────

function toSlug(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9\s-]/g, ' ')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

/** Return true only if the text actually contains chord markers (not just plain lyrics). */
function hasChordContent(text: string): boolean {
  // Chord-only lines: standalone tokens like Am, Em7, C#m, G/B
  const CHORD_TOKEN = /\b[A-G][b#]?(?:m(?:aj)?[0-9]*|M(?:aj)?[0-9]*|dim[0-9]*|aug[0-9]*|sus[24]?|add[0-9]+|[0-9]+)?(?:\/[A-G][b#]?)?\b/;
  const CHORD_ONLY_LINE = /^[A-G][b#]?[\w#b/\s]*$/;
  const lines = text.split('\n');
  const chordLines = lines.filter((l) => {
    const t = l.trim();
    if (!t || t.length > 80) return false;
    const tokens = t.split(/\s+/);
    const chordTokens = tokens.filter((tk) => CHORD_TOKEN.test(tk) && /^[A-G]/.test(tk));
    return chordTokens.length >= 1 && chordTokens.length / tokens.length >= 0.5;
  });
  // Also check for inline [Am] notation
  const hasInline = /\[[A-G][^\]]*\]/.test(text);
  return hasInline || chordLines.length >= 2;
}

/** Generate artist slug variants: eagles → [eagles, the-eagles] */
function artistVariants(artist: string): string[] {
  const base = toSlug(artist);
  const noThe = base.startsWith('the-') ? base.slice(4) : base;
  const withThe = base.startsWith('the-') ? base : `the-${base}`;
  return [...new Set([base, noThe, withThe])];
}

// ─── CifraClub — parse one song page ─────────────────────────────────────────

async function parseCifraPage(html: string): Promise<string | null> {
  // ── Method A: __NEXT_DATA__ (most reliable, bypasses JS rendering) ──
  const nd = extractNextData(html);
  if (nd) {
    // Navigate all known paths where CifraClub stores chord body
    /* eslint-disable @typescript-eslint/no-explicit-any */
    const paths: ((d: any) => any)[] = [
      (d) => d?.props?.pageProps?.data?.cifra?.body,
      (d) => d?.props?.pageProps?.initialState?.cifra?.body,
      (d) => d?.props?.pageProps?.cifra?.body,
      (d) => d?.props?.pageProps?.data?.body,
      (d) => d?.props?.pageProps?.cifra?.content,
      (d) => d?.props?.pageProps?.data?.cifra?.content,
    ];
    /* eslint-enable @typescript-eslint/no-explicit-any */

    for (const fn of paths) {
      const raw = fn(nd);
      if (typeof raw === 'string' && raw.length > 60) {
        const converted = convertProSheet(raw);
        if (converted.length > 60) {
          console.log('[CifraClub] ✓ __NEXT_DATA__ — length:', converted.length);
          return converted;
        }
      }
    }
  }

  // ── Method B: CSS-selector HTML parsing ──
  const { load } = await import('cheerio');
  const $ = load(html);

  const selectors = [
    '#cifra_cnt',
    '.g-cifra-outer',
    '.cifra_cnt',
    '[class*="CifraContainer"]',
    '[class*="cifra-outer"]',
    '.letra',
    'article pre',
    'pre',
  ];

  for (const sel of selectors) {
    const el = $(sel).first();
    if (!el.length) continue;
    // Convert <b>CHORD</b> → plain CHORD (preserves surrounding spaces)
    el.find('b').each((_, node) => {
      const c = $(node).text().trim();
      if (c) $(node).replaceWith(c);
    });
    el.find('br').replaceWith('\n');
    const text = el.text().replace(/\n{3,}/g, '\n\n').trim();
    if (text.length > 80) {
      console.log('[CifraClub] ✓ HTML selector:', sel, '— length:', text.length);
      return text;
    }
  }

  return null;
}

// ─── CifraClub — search then fetch ───────────────────────────────────────────

async function scrapeCifraClub(title: string, artist: string): Promise<{ chords: string; source: string } | null> {
  console.log('[CifraClub] Fetching:', artist, '—', title);

  const titleSlug = toSlug(title);
  const variants = artist ? artistVariants(artist) : [toSlug(title)];

  // 1 — fast path: try every artist-slug variant
  for (const aSlug of variants) {
    if (!aSlug || !titleSlug) continue;
    const url = `https://www.cifraclub.com/${aSlug}/${titleSlug}/`;
    console.log('[CifraClub] Trying:', url);
    const html = await fetchHtml(url, { Referer: 'https://www.cifraclub.com/' });
    if (!html) continue;
    const text = await parseCifraPage(html);
    if (text && hasChordContent(text)) return { chords: text, source: 'cifraclub' };
    if (text) console.log('[CifraClub] Content has no chord markers at:', url);
    else console.log('[CifraClub] No chord data at:', url);
  }

  // 2 — search page (extract results from __NEXT_DATA__)
  const q = `${artist} ${title}`.trim();
  const searchUrl = `https://www.cifraclub.com/busca/?q=${encodeURIComponent(q)}`;
  console.log('[CifraClub] Searching:', searchUrl);
  const searchHtml = await fetchHtml(searchUrl, { Referer: 'https://www.cifraclub.com/' });
  if (!searchHtml) return null;

  let songUrl: string | null = null;

  // Try __NEXT_DATA__ search results first (most accurate)
  const nd = extractNextData(searchHtml);
  if (nd) {
    /* eslint-disable @typescript-eslint/no-explicit-any */
    const resultLists: ((d: any) => any[])[] = [
      (d) => d?.props?.pageProps?.data?.items,
      (d) => d?.props?.pageProps?.data?.songs,
      (d) => d?.props?.pageProps?.initialState?.search?.results,
    ];
    /* eslint-enable @typescript-eslint/no-explicit-any */
    for (const fn of resultLists) {
      const items = fn(nd);
      if (Array.isArray(items) && items.length > 0) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const first = items.find((i: any) => i?.url && !String(i.url).includes('undefined'));
        if (first?.url) {
          songUrl = String(first.url).startsWith('http')
            ? first.url
            : `https://www.cifraclub.com${first.url}`;
          console.log('[CifraClub] Song URL from __NEXT_DATA__:', songUrl);
          break;
        }
      }
    }
  }

  // Fall back to HTML link scraping (filter out broken JS-template hrefs)
  if (!songUrl) {
    const { load } = await import('cheerio');
    const $s = load(searchHtml);
    const link = $s('a[href]').filter((_, el) => {
      const href = $s(el).attr('href') ?? '';
      return (
        !href.includes('undefined') &&
        (/^https?:\/\/www\.cifraclub\.com\/[^/?#]{2,}\/[^/?#]{2,}\/?$/.test(href) ||
          /^\/[^/?#]{2,}\/[^/?#]{2,}\/$/.test(href))
      );
    }).first().attr('href');
    if (link) {
      songUrl = link.startsWith('http') ? link : `https://www.cifraclub.com${link}`;
      console.log('[CifraClub] Song URL from HTML link:', songUrl);
    }
  }

  if (!songUrl) { console.log('[CifraClub] Search returned no usable URL'); return null; }

  const songHtml = await fetchHtml(songUrl, { Referer: searchUrl });
  if (!songHtml) return null;
  const text = await parseCifraPage(songHtml);
  if (!text || !hasChordContent(text)) return null;
  return { chords: text, source: 'cifraclub' };
}

// ─── AZChords fallback ────────────────────────────────────────────────────────

async function scrapeAZChords(title: string, artist: string): Promise<{ chords: string; source: string } | null> {
  console.log('[AZChords] Searching:', artist, '—', title);
  try {
    const q = `${artist} ${title}`.trim();
    const searchHtml = await fetchHtml(
      `https://www.azchords.com/search/?q=${encodeURIComponent(q)}`,
      { Referer: 'https://www.azchords.com/' }
    );
    if (!searchHtml) return null;

    const { load } = await import('cheerio');
    const $s = load(searchHtml);

    // AZChords result rows: links with artist/song in the href path
    const link = $s('a[href*="-tabs-"]').first().attr('href');
    if (!link) { console.log('[AZChords] No results'); return null; }

    const songUrl = link.startsWith('http') ? link : `https://www.azchords.com${link}`;
    console.log('[AZChords] Song URL:', songUrl);

    const songHtml = await fetchHtml(songUrl, { Referer: 'https://www.azchords.com/' });
    if (!songHtml) return null;

    const $p = load(songHtml);

    // AZChords wraps chords in <b> inside #tablatura
    $p('#tablatura b, #cont b').each((_, el) => {
      const c = $p(el).text().trim();
      if (c) $p(el).replaceWith(c);
    });
    $p('br').replaceWith('\n');

    const text = (
      $p('#tablatura').text() ||
      $p('#cont pre').text() ||
      $p('pre.tab').text()
    ).replace(/\n{3,}/g, '\n\n').trim();

    if (text.length < 80 || !hasChordContent(text)) { console.log('[AZChords] Content too short or no chords'); return null; }
    console.log('[AZChords] ✓ length:', text.length);
    return { chords: text, source: 'azchords' };
  } catch (err) {
    console.error('[AZChords] Error:', (err as Error).message);
    return null;
  }
}

// ─── Chordie fallback ─────────────────────────────────────────────────────────
// Chordie is an aggregator of public guitar tabs. Its pages use .textline and
// .chordline divs with inline [Am] span notation — easy to reconstruct as text.

async function scrapeChordie(title: string, artist: string): Promise<{ chords: string; source: string } | null> {
  const q = `${artist} ${title}`.trim();
  console.log('[Chordie] Searching:', q);
  try {
    const searchHtml = await fetchHtml(
      `https://www.chordie.com/results.php?q=${encodeURIComponent(q)}`,
      { Referer: 'https://www.chordie.com/' }
    );
    if (!searchHtml) return null;

    const { load } = await import('cheerio');
    const $s = load(searchHtml);

    // Result links are /chord.pere/<source-url>; pick the first one whose URL
    // contains ALL significant title words (length > 2) to avoid false matches.
    const titleWords = toSlug(title).split('-').filter((w) => w.length > 1);
    const songPath = titleWords.length > 0
      ? $s('a[href^="/chord.pere/"]').filter((_, el) => {
          const h = ($s(el).attr('href') ?? '').toLowerCase();
          return titleWords.every((w) => h.includes(w));
        }).first().attr('href')
      : $s('a[href^="/chord.pere/"]').first().attr('href');
    if (!songPath) { console.log('[Chordie] No matching results for:', title); return null; }

    const songUrl = `https://www.chordie.com${songPath}`;
    console.log('[Chordie] Fetching:', songUrl);

    const songHtml = await fetchHtml(songUrl, { Referer: 'https://www.chordie.com/results.php' });
    if (!songHtml) return null;
    const $p = load(songHtml);

    const lines: string[] = [];
    $p('.textline, .chordline').each((_, el) => {
      const isChordLine = $p(el).hasClass('chordline');
      if (isChordLine) {
        // extract chord spans and reconstruct [Am] notation
        let line = '';
        $p(el).contents().each((__, node) => {
          if (node.type === 'text') {
            line += $p(node).text();
          } else if ($p(node).find('.absc, [class*="abs"]').length) {
            const chord = $p(node).find('.absc, [class*="abs"]').first().text().trim();
            if (chord) line += `[${chord}]`;
          }
        });
        lines.push(line);
      } else {
        lines.push($p(el).text());
      }
    });

    const text = lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    if (!text || !hasChordContent(text)) {
      console.log('[Chordie] No chord content extracted');
      return null;
    }
    console.log('[Chordie] ✓ length:', text.length);
    return { chords: text, source: 'chordie' };
  } catch (err) {
    console.error('[Chordie]', (err as Error).message);
    return null;
  }
}

// ─── Ultimate Guitar scraper (via curl — bypasses Cloudflare) ────────────────
// UG embeds ALL page data as HTML-entity-encoded JSON in <div class="js-store"
// data-content="...">.  We extract that, parse it, and navigate to the chord
// content.  The tab content uses [ch]Am[/ch] for chord names and [tab]…[/tab]
// for tablature blocks.

function decodeHtmlEntities(s: string): string {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&#039;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractUGStore(html: string): any | null {
  const m = html.match(/<div\s+class="js-store"\s+data-content="([^"]+)"/);
  if (!m) return null;
  try {
    return JSON.parse(decodeHtmlEntities(m[1]));
  } catch { return null; }
}

function convertUGContent(raw: string): string {
  return raw
    .replace(/\r\n/g, '\n')
    .replace(/\[ch\]([^\[]+)\[\/ch\]/g, '$1')   // [ch]Am[/ch] → Am
    .replace(/\[tab\]([\s\S]*?)\[\/tab\]/g, '$1') // [tab]…[/tab] → content
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function scrapeUltimateGuitar(title: string, artist: string): Promise<{ chords: string; source: string } | null> {
  console.log('[UG] Searching:', title, artist ? `(artist: ${artist})` : '');

  // UG's search_type=title filters by song title only — including the artist
  // name in the value returns zero results. Search by title, then pick the
  // best match (preferring the correct artist when known).
  const searchUrl = `https://www.ultimate-guitar.com/search.php?search_type=title&value=${encodeURIComponent(title)}`;
  const searchHtml = await curlFetch(searchUrl);
  if (!searchHtml) { console.log('[UG] Search fetch failed'); return null; }

  const searchStore = extractUGStore(searchHtml);
  if (!searchStore) { console.log('[UG] No js-store on search page'); return null; }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const results: any[] = searchStore?.store?.page?.data?.results ?? [];
  if (!results.length) { console.log('[UG] No search results'); return null; }

  // Prefer Chords type, then Tabs; pick highest-rated
  const chordResults = results.filter((r) => r.type === 'Chords' && r.tab_access_type === 'public' && r.tab_url);
  const tabResults   = results.filter((r) => r.type === 'Tabs'   && r.tab_access_type === 'public' && r.tab_url);
  let candidates = chordResults.length ? chordResults : tabResults;
  if (!candidates.length) { console.log('[UG] No public chords/tabs in results'); return null; }

  // If we know the artist, prefer results whose artist_name contains it
  if (artist) {
    const aSlug = toSlug(artist);
    const artistMatches = candidates.filter((r) =>
      toSlug(r.artist_name ?? '').includes(aSlug.split('-')[0]) ||
      aSlug.includes(toSlug(r.artist_name ?? '').split('-')[0])
    );
    if (artistMatches.length) candidates = artistMatches;
  }

  // Sort by votes descending
  candidates.sort((a, b) => (b.votes ?? 0) - (a.votes ?? 0));
  const best = candidates[0];
  console.log('[UG] Best result:', best.song_name, '— votes:', best.votes, '—', best.tab_url);

  // ── Step 2: tab page ──
  const tabHtml = await curlFetch(best.tab_url);
  if (!tabHtml) { console.log('[UG] Tab page fetch failed'); return null; }

  const tabStore = extractUGStore(tabHtml);
  if (!tabStore) { console.log('[UG] No js-store on tab page'); return null; }

  // Navigate possible paths for tab content
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const paths: ((d: any) => any)[] = [
    (d) => d?.store?.page?.data?.tab_view?.wiki_tab?.content,
    (d) => d?.store?.page?.data?.tab?.content,
    (d) => d?.store?.page?.data?.tab_view?.applicature,
  ];
  /* eslint-enable @typescript-eslint/no-explicit-any */

  for (const fn of paths) {
    const raw = fn(tabStore);
    if (typeof raw === 'string' && raw.length > 60) {
      const converted = convertUGContent(raw);
      if (converted.length > 60 && hasChordContent(converted)) {
        console.log('[UG] ✓ length:', converted.length);
        return { chords: converted, source: 'ultimate-guitar' };
      }
    }
  }

  console.log('[UG] No usable chord content in tab page');
  return null;
}

function looksIndian(q: string): boolean {
  if (/[ऀ-ॿ]/.test(q)) return true;
  const kw = [
    'hindi', 'bollywood', 'punjabi', 'marathi', 'telugu', 'tamil', 'kannada',
    'malayalam', 'bengali', 'filmy',
    // Popular Indian artists
    'arijit', 'kishore', 'lata', 'atif', 'shreya', 'ajay', 'atul',
    'sonu nigam', 'armaan malik', 'jubin', 'neha kakkar', 'udit narayan',
    'a.r. rahman', 'ar rahman', 'shankar ehsaan', 'vishal shekhar',
    'pritam', 'anu malik', 'himesh',
  ];
  return kw.some((k) => q.toLowerCase().includes(k));
}

// ─── HarpTabs (harmonica) ─────────────────────────────────────────────────────
// HarpTabs uses Cloudflare — must use curlFetch (system curl bypasses JA3 check).
// Search endpoint: /?search_string=... (root path, not /search.php)
// Song pages: /song.php?ID=XXX
// Content: inline HTML with <br> line breaks and &nbsp; spaces, in a <td>

const HARPTABS_REFERER = ['-H', 'Referer: https://www.harptabs.com/'];

// When HarpTabs internal search returns zero results (common for long Romanized Hindi titles),
// fall back to DuckDuckGo HTML search to locate the song.php?ID= URL directly.
async function harptabsDdgFallback(query: string): Promise<string | null> {
  console.log('[HarpTabs/DDG] Falling back to DuckDuckGo for:', query);
  const ddgHtml = await curlFetch(
    `https://html.duckduckgo.com/html/?q=${encodeURIComponent(`site:harptabs.com ${query}`)}`,
    ['-H', 'Referer: https://duckduckgo.com/', '-H', 'Accept-Language: en-US,en;q=0.9']
  );
  if (!ddgHtml) return null;

  const { load: loadDDG } = await import('cheerio');
  const $d = loadDDG(ddgHtml);

  // DDG result links are either direct hrefs or /l/?uddg=URL-encoded-redirect.
  // Decode every <a href> and look for harptabs.com/song.php?ID=NNN.
  const SONG_ID_RE = /harptabs\.com\/song\.php\?ID=(\d+)/i;
  let songId: string | null = null;

  $d('a[href]').each((_, el) => {
    if (songId) return;
    const raw = $d(el).attr('href') ?? '';
    // Try direct match first
    let m = raw.match(SONG_ID_RE);
    if (m) { songId = m[1]; return; }
    // DDG wraps results in /l/?uddg=<percent-encoded URL> — decode and retry
    try {
      const decoded = decodeURIComponent(raw);
      m = decoded.match(SONG_ID_RE);
      if (m) { songId = m[1]; return; }
    } catch { /* malformed encoding — skip */ }
  });

  // Last-resort raw-HTML scan (catches URLs in <span class="result__url"> etc.)
  if (!songId) {
    const m = ddgHtml.match(SONG_ID_RE);
    if (m) songId = m[1];
  }

  if (!songId) { console.log('[HarpTabs/DDG] No harptabs song.php?ID= link found'); return null; }
  const url = `https://www.harptabs.com/song.php?ID=${songId}`;
  console.log('[HarpTabs/DDG] Found:', url);
  return url;
}

async function scrapeHarpTabs(title: string, artist: string): Promise<{ chords?: string; tabUrl?: string; source: string } | null> {
  console.log('[HarpTabs] Searching title:', title, artist ? `(artist: ${artist})` : '');

  // ── Step 1: Native HarpTabs search — title only (more reliable than title+artist) ──
  const searchHtml = await curlFetch(
    `https://www.harptabs.com/?search_string=${encodeURIComponent(title)}`,
    HARPTABS_REFERER
  );

  if (!searchHtml || searchHtml.length < 500) {
    console.log('[HarpTabs] Search unreachable — returning fallback link');
    return { tabUrl: `https://www.harptabs.com/?search_string=${encodeURIComponent(title)}`, source: 'harptabs' };
  }

  const { load } = await import('cheerio');
  const $s = load(searchHtml);
  const allLinks = $s('a[href*="song.php?ID="]');

  let songUrl: string;

  if (allLinks.length === 0) {
    // ── Step 2: 0 native results → DDG site-search fallback ──
    console.log('[HarpTabs] 0 native results — trying DDG fallback');
    const ddgUrl = await harptabsDdgFallback(`${title}${artist ? ' ' + artist : ''}`);
    if (!ddgUrl) {
      console.log('[HarpTabs] DDG also found nothing — returning null');
      return null;
    }
    songUrl = ddgUrl;
  } else {
    // ── Native results exist — require a title-word match (no ghost-data fallback) ──
    const titleWords = toSlug(title).split('-').filter((w) => w.length > 1);
    const matchedLink = allLinks.filter((_, el) => {
      const text = toSlug($s(el).text());
      return titleWords.length > 0
        ? titleWords.every((w) => text.includes(w))
        : text.length > 0;
    }).first();

    const rawLink = matchedLink.length ? matchedLink.attr('href') : undefined;
    if (!rawLink) {
      console.log('[HarpTabs] Results found but none matched title words — returning null');
      return null;
    }
    console.log('[HarpTabs] Matched result:', matchedLink.text() || rawLink);
    songUrl = rawLink.startsWith('http') ? rawLink : `https://www.harptabs.com/${rawLink.replace(/^\//, '')}`;
  }
  console.log('[HarpTabs] Fetching song page:', songUrl);

  const songHtml = await curlFetch(songUrl, HARPTABS_REFERER);
  if (!songHtml) return { tabUrl: songUrl, source: 'harptabs' };

  const $p = load(songHtml);

  // HarpTabs page layout:
  //   Left column  -- navigation sidebar (<td width=75 background=spacer.gif>)
  //   Center column -- song metadata + actual tab content (<td valign=top align=center>)
  //   Right column -- ads
  //
  // All columns contain <br> tags and HTML like `font size=-1` which contains
  // digit patterns, so we cannot use innerHTML regex to discriminate.
  // Instead: decode each <td> to plain text and look for NOTATION LINES --
  // lines that contain only digits, spaces, + and - (e.g. " 6  -6  7 -7").
  // The sidebar text is "Homepage", "Account", etc. -- zero notation lines.

  const NAV_WORDS = /^\s*(homepage|account|inbox|compose|login|new user|tabs listing|list all tabs|tabs by letter|view files|search tabs|random tab|contribute|forum|add a tab|my drafts|post a file|resources|site blog|youtube feed|tab guide|player list|member list|member map|links|tab rulers|mobile site|tab tool|website|add-ons|store|contact us)\s*$/i;

  let tabText = '';
  $p('td').each((_, el) => {
    const inner = $p(el).html() ?? '';
    if (!inner.includes('<br')) return;

    // Decode to plain text via string manipulation -- avoid mutating the cheerio DOM
    const text = inner
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/&nbsp;/gi, ' ')
      .replace(/&#160;/g, ' ')
      .replace(/<[^>]+>/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    const lines = text.split('\n');

    // A notation line is entirely digits, spaces, +, and - with at least one digit
    const notationLines = lines.filter((l) => {
      const t = l.trim();
      return t.length >= 2 && /^[\d +\-]+$/.test(t) && /\d/.test(t);
    });

    // Require >= 3 pure notation lines; reject if dominated by nav menu words
    if (notationLines.length < 3) return;
    const navLines = lines.filter((l) => NAV_WORDS.test(l));
    if (navLines.length > notationLines.length) return;

    if (text.length > tabText.length) tabText = text;
  });

  if (tabText.length > 20) {
    // Strip the page chrome that precedes the actual tab:
    // "Add to Favorites | ... | Report Tab", "Tweet", metadata block, rating widget
    // The actual content starts at the "Song:" label (if present)
    const songStart = tabText.indexOf('\nSong:\n');
    if (songStart !== -1) tabText = tabText.slice(songStart + 1);
    // Strip trailing fav-count footer
    tabText = tabText.replace(/\n\d+ user\(s\) have favorited this tab\s*$/i, '').trim();
    console.log('[HarpTabs] OK length:', tabText.length);
    return { chords: tabText, tabUrl: songUrl, source: 'harptabs' };
  }

  // Page fetched successfully but no harmonica notation found in it
  console.log('[HarpTabs] Page found but no notation content — returning tabUrl for manual lookup');
  return { tabUrl: songUrl, source: 'harptabs' };
}

// ─── Songsterr embed ID ───────────────────────────────────────────────────────

async function getSongsterrId(query: string): Promise<number | null> {
  try {
    const res = await fetch(`https://www.songsterr.com/a/ra/songs.json?pattern=${encodeURIComponent(query)}`, {
      signal: AbortSignal.timeout(6000),
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible)' },
    });
    if (!res.ok) return null;
    const data = await res.json();
    const id = Array.isArray(data) ? data[0]?.id : null;
    if (id) console.log('[Songsterr] Found ID:', id);
    return id ?? null;
  } catch { return null; }
}

// ─── Route ────────────────────────────────────────────────────────────────────

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const q = searchParams.get('q') ?? '';
  const instrument = searchParams.get('instrument') ?? 'guitar';
  const title = searchParams.get('title') ?? q;
  const artist = searchParams.get('artist') ?? '';
  if (!q) return NextResponse.json({ error: 'query required' }, { status: 400 });

  console.log(`\n[chords] ── ${instrument}  "${q}" ──`);

  if (instrument === 'harmonica') {
    const r = await scrapeHarpTabs(title, artist);
    return NextResponse.json(r ?? { chords: null });
  }

  const isIndian = looksIndian(q);
  let chordResult: { chords: string; source: string } | null = null;

  // For Indian songs go straight to UG (CifraClub has no Bollywood data).
  // For all others, try CifraClub first (faster + no subprocess overhead).
  // Songsterr embed ID runs in parallel regardless.
  const [cfResult, ssId] = await Promise.all([
    isIndian ? Promise.resolve(null) : scrapeCifraClub(title, artist),
    instrument === 'guitar' ? getSongsterrId(q) : Promise.resolve(null),
  ]);
  chordResult = cfResult;

  if (!chordResult) {
    // UG is tried second for Indian songs (primary fallback) and third overall
    // (after CifraClub and AZChords) for Western songs.
    if (isIndian) {
      console.log('[chords] Indian song — trying Ultimate Guitar first');
      chordResult = await scrapeUltimateGuitar(title, artist);
    } else {
      console.log('[chords] CifraClub failed — trying AZChords');
      chordResult = await scrapeAZChords(title, artist);
    }
  }

  if (!chordResult && !isIndian) {
    console.log('[chords] AZChords failed — trying Chordie');
    chordResult = await scrapeChordie(title, artist);
  }

  if (!chordResult && !isIndian) {
    console.log('[chords] Chordie failed — trying Ultimate Guitar');
    chordResult = await scrapeUltimateGuitar(title, artist);
  }

  // Last resort for Indian: try CifraClub (occasionally has Bollywood tabs)
  if (!chordResult && isIndian) {
    chordResult = await scrapeCifraClub(title, artist);
  }

  console.log(`[chords] ✓ source=${chordResult?.source ?? 'none'}  ssId=${ssId ?? 'none'}`);
  return NextResponse.json({
    chords: chordResult?.chords ?? null,
    source: chordResult?.source ?? null,
    songsterrId: ssId ?? undefined,
  });
}
