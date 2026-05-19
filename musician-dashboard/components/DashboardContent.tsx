'use client';

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import WaveformLoader from '@/components/WaveformLoader';
import YoutubePlayer from '@/components/YoutubePlayer';
import LyricsWithChords from '@/components/LyricsWithChords';
import DashboardNav from '@/components/DashboardNav';
import { SongData, Instrument } from '@/lib/types';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

// Strip YouTube metadata noise from manually-typed queries.
// Autocomplete suggestions already carry clean title/artist separately,
// so this only runs on free-text input.
function sanitizeSearchQuery(q: string): string {
  return q
    // Strip "| Label / Channel" and everything after
    .replace(/\s*\|.*$/, '')
    // Strip trailing parenthetical qualifiers (Official Audio, Full Song, etc.)
    .replace(/\s*[\(\[](?:full\s+song|official\s+(?:audio|video|music\s+video)|lyric\s+video|audio\s+song|title\s+song|theme\s+song)[^\)\]]*[\)\]]/gi, '')
    // Strip standalone noise phrases
    .replace(/\b(?:full\s+song|official\s+(?:audio|video)|lyric\s+video|audio\s+song|title\s+song)\b/gi, '')
    // Strip well-known music labels (common in Indian YT titles)
    .replace(/\b(?:sony\s+music(?:\s+india)?|t-?series|zee\s+music\s+company|saregama|tips\s+music|eros\s+(?:music|now)|yrf|dharma\s+productions?|red\s+ribbon|junglee\s+music|speed\s+records|desi\s+music\s+factory)\b/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

export default function DashboardContent() {
  const params = useSearchParams();
  const query = params.get('q') || '';
  const instrument = (params.get('instrument') || 'guitar') as Instrument;
  // Explicit title/artist are set by the autocomplete — they are already clean.
  // For manual searches these are absent and we parse from the query instead.
  const urlTitle = params.get('title') || '';
  const urlArtist = params.get('artist') || '';

  const [loading, setLoading] = useState(true);
  const [songData, setSongData] = useState<SongData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!query) {
      setError('No search query provided.');
      setLoading(false);
      return;
    }
    fetchAll(query, instrument);
  }, [query, instrument]);

  async function fetchAll(q: string, inst: Instrument) {
    setLoading(true);
    setSongData(null);
    setError(null);

    // Prefer explicit title/artist from autocomplete URL params (already clean).
    // For manual queries, sanitize the raw string then split on the first " - ".
    let title: string;
    let artist: string;
    if (urlTitle) {
      title = urlTitle;
      artist = urlArtist;
    } else {
      const clean = sanitizeSearchQuery(q);
      const dashIdx = clean.indexOf(' - ');
      title = dashIdx >= 0 ? clean.slice(0, dashIdx).trim() : clean.trim();
      artist = dashIdx >= 0 ? clean.slice(dashIdx + 3).trim() : '';
    }

    try {
      const [audioResult, lyricsResult, chordsResult] = await Promise.allSettled([
        fetch(`/api/audio?q=${encodeURIComponent(q)}`).then((r) => r.json()),
        fetch(
          `/api/lyrics?title=${encodeURIComponent(title)}&artist=${encodeURIComponent(artist)}`
        ).then((r) => r.json()),
        fetch(
          `/api/chords?q=${encodeURIComponent(q)}&instrument=${inst}&title=${encodeURIComponent(title)}&artist=${encodeURIComponent(artist)}`
        ).then((r) => r.json()),
      ]);

      const audio = audioResult.status === 'fulfilled' ? audioResult.value : null;
      const lyrics = lyricsResult.status === 'fulfilled' ? lyricsResult.value : null;
      const chords = chordsResult.status === 'fulfilled' ? chordsResult.value : null;

      setSongData({
        title,
        artist,
        instrument: inst,
        query: q,
        videoId: audio?.videoId,
        videoTitle: audio?.title,
        lyrics: lyrics?.lyrics ?? undefined,
        chords: chords?.chords ?? undefined,
        songsterrId: chords?.songsterrId ?? undefined,
        tabUrl: chords?.tabUrl ?? undefined,
      });
    } catch {
      setError('Something went wrong loading the song data. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <WaveformLoader query={query} instrument={instrument} />;

  if (error || !songData) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="w-14 h-14 text-red-500 mb-4 opacity-70" />
        <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
        <p className="text-gray-400 mb-6">{error || 'Unknown error'}</p>
        <Link
          href="/"
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Try Again
        </Link>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-950 flex flex-col">
      <DashboardNav songData={songData} />

      {/* Main scrollable content — min-h-0 keeps flex-1 from overflowing h-screen */}
      <main ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto pb-[280px]">
        <LyricsWithChords songData={songData} scrollContainerRef={scrollRef} />
      </main>

      {/* Sticky bottom player */}
      <div className="fixed bottom-0 inset-x-0 z-50">
        <YoutubePlayer
          videoId={songData.videoId}
          title={songData.videoTitle}
          artist={songData.artist}
        />
      </div>
    </div>
  );
}
