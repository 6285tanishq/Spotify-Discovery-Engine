import { NextRequest, NextResponse } from 'next/server';

// ─── Genius API + page scraper ────────────────────────────────────────────────

async function fetchFromGenius(title: string, artist: string): Promise<string | null> {
  const token = process.env.GENIUS_API_TOKEN;
  if (!token || token === 'PASTE_YOUR_GENIUS_TOKEN_HERE') {
    console.log('[lyrics/genius] No API token configured — skipping');
    return null;
  }

  const query = [artist, title].filter(Boolean).join(' ');
  console.log('[lyrics/genius] Searching for:', query);

  try {
    // Step 1: Search the Genius API
    const searchRes = await fetch(
      `https://api.genius.com/search?q=${encodeURIComponent(query)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(8000),
      }
    );

    if (!searchRes.ok) {
      console.log('[lyrics/genius] Search API error:', searchRes.status);
      return null;
    }

    const searchJson = await searchRes.json();
    const hit = searchJson?.response?.hits?.[0];

    if (!hit) {
      console.log('[lyrics/genius] No hits found for:', query);
      return null;
    }

    const songUrl: string = hit.result.url;
    const songTitle: string = hit.result.full_title;
    console.log('[lyrics/genius] Found:', songTitle, '—', songUrl);

    // Step 2: Scrape the Genius page for actual lyrics
    const pageRes = await fetch(songUrl, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        Accept: 'text/html',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!pageRes.ok) {
      console.log('[lyrics/genius] Page fetch failed:', pageRes.status);
      return null;
    }

    const html = await pageRes.text();
    const { load } = await import('cheerio');
    const $ = load(html);

    const chunks: string[] = [];

    // Genius renders lyrics in divs with data-lyrics-container="true"
    $('[data-lyrics-container="true"]').each((_, el) => {
      $(el).find('br').replaceWith('\n');
      $(el).find('a').each((_i, a) => { $(a).replaceWith($(a).text()); });
      chunks.push($(el).text());
    });

    // Fallback selectors for older/alternate Genius page layouts
    if (chunks.length === 0) {
      $('[class*="Lyrics__Container"], .lyrics').each((_, el) => {
        $(el).find('br').replaceWith('\n');
        chunks.push($(el).text());
      });
    }

    if (chunks.length === 0) {
      console.log('[lyrics/genius] No lyrics container found on page');
      return null;
    }

    let lyrics = chunks.join('\n\n');

    // Genius prepends a metadata block like "164 ContributorsTranslationsEspañol..."
    // before the actual song lines. Strip it by working line-by-line.
    const METADATA_LINE = /^\d+\s*Contributor|^Translations?$|^Espa[ñn]ol$|^Deutsch$|^Portugu[eê]s$|^Polski$|^Italiano$|^T[üu]rk[cç]e$|^日本語$|^[Рр]усский$|^हिन्दी$|^فارسی$|^[؀-ۿݐ-ݿ]+$/i;

    const lines = lyrics.split('\n');
    // Find the first index that looks like a real lyric line (not metadata)
    let startIdx = 0;
    for (let i = 0; i < lines.length; i++) {
      const l = lines[i].trim();
      if (l && !METADATA_LINE.test(l)) { startIdx = i; break; }
    }
    lyrics = lines.slice(startIdx).join('\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    if (!lyrics) {
      console.log('[lyrics/genius] Content became empty after stripping metadata');
      return null;
    }

    console.log('[lyrics/genius] Successfully extracted lyrics, length:', lyrics.length);
    return lyrics;
  } catch (err) {
    console.error('[lyrics/genius] Error:', err);
    return null;
  }
}

// ─── lyrics.ovh fallback ─────────────────────────────────────────────────────

async function fetchFromLyricsOvh(title: string, artist: string): Promise<string | null> {
  if (!title) return null;
  console.log('[lyrics/ovh] Trying lyrics.ovh for:', artist, '—', title);

  try {
    const a = encodeURIComponent(artist || title);
    const t = encodeURIComponent(title);
    const res = await fetch(`https://api.lyrics.ovh/v1/${a}/${t}`, {
      signal: AbortSignal.timeout(7000),
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.lyrics) {
      console.log('[lyrics/ovh] Found lyrics, length:', data.lyrics.length);
      return data.lyrics as string;
    }
    return null;
  } catch (err) {
    console.error('[lyrics/ovh] Error:', err);
    return null;
  }
}

// ─── Route handler ────────────────────────────────────────────────────────────

export async function GET(request: NextRequest) {
  const title = request.nextUrl.searchParams.get('title') ?? '';
  const artist = request.nextUrl.searchParams.get('artist') ?? '';

  if (!title) return NextResponse.json({ error: 'title required' }, { status: 400 });

  // Genius first (richer lyrics, handles Bollywood/Hindi), then ovh fallback
  const lyrics =
    (await fetchFromGenius(title, artist)) ??
    (await fetchFromLyricsOvh(title, artist));

  if (lyrics) return NextResponse.json({ lyrics });

  console.log('[lyrics] All sources failed for:', artist, '—', title);
  return NextResponse.json({ lyrics: null, error: 'Lyrics not found' });
}
