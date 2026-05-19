import { NextRequest, NextResponse } from 'next/server';

// ─── Cleaning helpers ─────────────────────────────────────────────────────────

// Known music label channels — when a video is uploaded by one of these,
// the real artist is usually embedded in the video title ("Artist - Song").
const LABEL_RE =
  /^(?:sony\s+music(?:\s+india)?|t-?series|zee\s+music(?:\s+company)?|saregama|tips\s+music|eros\s+(?:music|now)|yrf|dharma\s+productions?|red\s+ribbon|junglee\s+music|speed\s+records|desi\s+music\s+factory|audio\s+jukebox|universal\s+music(?:\s+india)?|warner\s+music(?:\s+india)?|capitol\s+records|atlantic\s+records)$/i;

function cleanTitle(raw: string): string {
  return raw
    // Strip " | channel / label suffix" first
    .replace(/\s*\|.*$/, '')
    // Strip any bracketed qualifier anywhere in the title
    .replace(/\s*[\(\[](?:Official|Original|Audio|Video|Lyrics?|Lyrical|HQ|HD|4K|Full\s+Song|Live|Remaster(?:ed)?|Visualizer|Animated)[^\)\]]*[\)\]]/gi, '')
    // Strip " - Noise Phrase" at end of title
    .replace(/\s*-\s*(?:full\s+song|lyrical?\s+(?:song|video)?|official\s+(?:audio|video|music\s+video)|title\s+song|theme\s+song|audio\s+song|video\s+song)\s*$/gi, '')
    // Strip trailing year "(2019)"
    .replace(/\s*\(\d{4}\)\s*$/, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function cleanChannel(name: string): string {
  return name
    .replace(/\s*-\s*topic$/i, '')
    .replace(/vevo$/i, '')
    .replace(/official$/i, '')
    .trim();
}

// Parse a cleaned video title + channel into { displayTitle, artist, query }.
// When the channel is a known label the real artist is often "Artist - Song" in the title.
function parseVideoMeta(
  rawTitle: string,
  rawChannel: string
): { title: string; artist: string; query: string } {
  const title = cleanTitle(rawTitle);
  const channel = cleanChannel(rawChannel);

  // If the channel is a label (not an artist), try to extract "Artist - Song" from the title
  if (LABEL_RE.test(channel) || !channel) {
    const dashIdx = title.indexOf(' - ');
    if (dashIdx > 0 && dashIdx < 50) {
      const maybeArtist = title.slice(0, dashIdx).trim();
      const maybeSong = cleanTitle(title.slice(dashIdx + 3));
      if (maybeSong.length > 1 && maybeArtist.length > 1) {
        const query = `${maybeSong} - ${maybeArtist}`;
        return { title: maybeSong, artist: maybeArtist, query };
      }
    }
    // Can't extract artist from title — return title only
    return { title, artist: '', query: title };
  }

  // Normal case: channel is the artist
  const query = channel && !title.toLowerCase().includes(channel.toLowerCase())
    ? `${title} - ${channel}`
    : title;
  return { title, artist: channel, query };
}

// ─── Route ───────────────────────────────────────────────────────────────────

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get('q') ?? '';
  if (q.length < 2) return NextResponse.json({ suggestions: [] });

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const ytSearch = require('yt-search') as (
      q: string
    ) => Promise<{
      videos: Array<{ videoId: string; title: string; author?: { name?: string } }>;
    }>;

    const result = await ytSearch(q);

    const seen = new Set<string>();
    const suggestions = result.videos
      .slice(0, 12)
      .map((v) => parseVideoMeta(v.title, v.author?.name ?? ''))
      .filter((s) => {
        if (!s.title || seen.has(s.query)) return false;
        seen.add(s.query);
        return true;
      })
      .slice(0, 5);

    return NextResponse.json({ suggestions });
  } catch {
    return NextResponse.json({ suggestions: [] });
  }
}
