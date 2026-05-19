import { NextRequest, NextResponse } from 'next/server';

type YTVideo = {
  videoId: string;
  title: string;
  duration?: { timestamp?: string };
  thumbnail?: string;
  author?: { name?: string };
};

/** Score a video — higher = more likely to be embeddable & audio-focused */
function scoreVideo(v: YTVideo): number {
  const title = v.title.toLowerCase();
  const channel = v.author?.name?.toLowerCase() ?? '';
  let score = 0;

  // Strongly prefer auto-generated Topic channels (always embeddable)
  if (channel.endsWith('- topic') || channel.includes('topic')) score += 40;

  // Prefer audio/lyric formats
  if (title.includes('official audio')) score += 30;
  if (title.includes('lyric video') || title.includes('lyrics')) score += 25;
  if (title.includes('audio')) score += 15;

  // Penalise official music videos — major labels block iframe embedding
  if (title.includes('official music video') || title.includes('official video')) score -= 30;
  if (title.includes('official mv')) score -= 25;

  // Penalise live / karaoke / cover
  if (title.includes('live') || title.includes('concert')) score -= 10;
  if (title.includes('karaoke') || title.includes('cover') || title.includes('remix')) score -= 5;

  return score;
}

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get('q');
  if (!q) return NextResponse.json({ error: 'Query required' }, { status: 400 });

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const ytSearch = require('yt-search') as (q: string) => Promise<{ videos: YTVideo[] }>;

    // Try three query variants in parallel and pick the best-scoring video overall
    const variants = [
      `${q} official audio`,
      `${q} lyric video`,
      `${q} lyrics`,
    ];

    console.log(`[audio] Searching YouTube for: "${q}"`);

    const pools = await Promise.allSettled(variants.map((v) => ytSearch(v)));

    const allVideos: YTVideo[] = [];
    for (const p of pools) {
      if (p.status === 'fulfilled') allVideos.push(...p.value.videos.slice(0, 5));
    }

    if (allVideos.length === 0) {
      // Last-resort: plain query
      const fallback = await ytSearch(q);
      allVideos.push(...fallback.videos.slice(0, 5));
    }

    // De-duplicate by videoId, then sort by score
    const seen = new Set<string>();
    const unique = allVideos.filter((v) => {
      if (seen.has(v.videoId)) return false;
      seen.add(v.videoId);
      return true;
    });

    unique.sort((a, b) => scoreVideo(b) - scoreVideo(a));

    const best = unique[0];
    if (!best) return NextResponse.json({ error: 'No videos found' }, { status: 404 });

    console.log(`[audio] Best match: "${best.title}" (score ${scoreVideo(best)}) — ${best.videoId}`);

    return NextResponse.json({
      videoId: best.videoId,
      title: best.title,
      duration: best.duration?.timestamp ?? null,
      thumbnail: best.thumbnail ?? null,
    });
  } catch (err) {
    console.error('[audio] Error:', err);
    return NextResponse.json({ error: 'Search failed' }, { status: 500 });
  }
}
