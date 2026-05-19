'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { BookOpen, Music, ExternalLink, Info, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { SongData, Instrument } from '@/lib/types';
import PracticeControls from '@/components/PracticeControls';

// ─── chord-detection helpers ──────────────────────────────────────────────────

// Matches standard chord names: Am, C#m, Gmaj7, Dsus4, F#/C, Bb7, etc.
const CHORD_RE =
  /\b([A-G][b#]?(?:m(?:aj)?[0-9]*|M(?:aj)?[0-9]*|dim[0-9]*|aug[0-9]*|sus[24]?|add[0-9]+|[0-9]+(?:sus[24]?)?)?(?:\/[A-G][b#]?)?)\b/g;

const SINGLE_CHORD_RE =
  /^[A-G][b#]?(?:m(?:aj)?[0-9]*|M(?:aj)?[0-9]*|dim[0-9]*|aug[0-9]*|sus[24]?|add[0-9]+|[0-9]+(?:sus[24]?)?)?(?:\/[A-G][b#]?)?$/;

function isChordOnlyLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return false;
  const tokens = trimmed.split(/\s+/).filter(Boolean);
  const chordCount = tokens.filter((t) => SINGLE_CHORD_RE.test(t)).length;
  // ≥ 50 % of tokens must be chord names, and there must be at least 1
  return chordCount >= 1 && chordCount / tokens.length >= 0.5;
}

// Inline [Am] markers (chordie / plain format)
type Segment = { chord: string | null; text: string };

function parseInlineChords(line: string): Segment[] {
  const tokens = line.split(/(\[[^\]]+\])/);
  const segments: Segment[] = [];
  let pendingChord: string | null = null;
  for (const t of tokens) {
    if (/^\[[A-G][^\]]*\]$/.test(t)) {
      pendingChord = t.slice(1, -1);
    } else {
      segments.push({ chord: pendingChord, text: t });
      pendingChord = null;
    }
  }
  if (pendingChord) segments.push({ chord: pendingChord, text: '' });
  return segments;
}

function hasInlineChords(line: string): boolean {
  return /\[[A-G][^\]]*\]/.test(line);
}

// ─── chord-line renderer ──────────────────────────────────────────────────────

/** Highlight standalone chords in a chord-only line, preserving whitespace. */
function HighlightedChordLine({ line }: { line: string }) {
  const parts = line.split(CHORD_RE);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <span
            key={i}
            className="bg-indigo-900/50 text-blue-300 font-bold rounded px-[3px] mx-[1px] border border-indigo-700/40"
          >
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

/** Inline [Am]word layout — chord name floated above the word. */
function InlineChordLine({ line }: { line: string }) {
  const segments = parseInlineChords(line);
  return (
    <span className="chord-line">
      {segments.map((seg, i) => (
        <span key={i} className="chord-segment">
          <span className="chord-name">{seg.chord ?? ' '}</span>
          <span className="chord-text">{seg.text || (seg.chord ? ' ' : '')}</span>
        </span>
      ))}
    </span>
  );
}

// ─── piano content filter ─────────────────────────────────────────────────────

function filterForPiano(content: string): string {
  return content
    .split('\n')
    .filter((line) => {
      const t = line.trim();
      // Guitar string notation: E|---, B|---, e|--- etc.
      if (/^[EBGDAe]\s*\|/.test(t)) return false;
      // Any line with tab-style |--- fret notation
      if (/\|[-─]{2,}/.test(line)) return false;
      // Capo instructions
      if (/capo/i.test(line)) return false;
      return true;
    })
    .join('\n');
}

// ─── full chord-sheet renderer ────────────────────────────────────────────────

function ChordSheet({ content, fontSize, instrument }: { content: string; fontSize: number; instrument?: string }) {
  const displayContent = instrument === 'piano' ? filterForPiano(content) : content;

  if (!displayContent?.trim()) {
    return (
      <div className="text-center py-16 text-gray-500">
        <Music className="w-10 h-10 mx-auto mb-3 opacity-30" />
        <p>No chord data found for this song.</p>
      </div>
    );
  }

  const lines = displayContent.split('\n');

  return (
    <pre
      className="font-mono whitespace-pre leading-[1.8] break-words"
      style={{ fontSize: `${fontSize}px` }}
    >
      {lines.map((line, i) => {
        const trimmed = line.trim();

        // Empty line → small gap
        if (!trimmed) return <span key={i} className="block h-[0.6em]" />;

        // Section headers like [Verse 1], [Chorus] — but not inline chords
        if (/^\[.+\]$/.test(trimmed) && !hasInlineChords(trimmed)) {
          return (
            <span key={i} className="block pt-4 pb-0.5">
              <span className="text-indigo-400 font-extrabold uppercase tracking-widest"
                style={{ fontSize: `${Math.max(10, fontSize - 2)}px` }}>
                {trimmed.slice(1, -1)}
              </span>
            </span>
          );
        }

        // Chord-only line (standard "chord above lyrics" format)
        if (isChordOnlyLine(trimmed)) {
          return (
            <span key={i} className="block">
              <HighlightedChordLine line={line} />
            </span>
          );
        }

        // Inline [Am]word format
        if (hasInlineChords(line)) {
          return (
            <span key={i} className="block">
              <InlineChordLine line={line} />
            </span>
          );
        }

        // Plain lyric line
        return (
          <span key={i} className="block text-gray-200">
            {line}
          </span>
        );
      })}
    </pre>
  );
}

// ─── tabs panel ───────────────────────────────────────────────────────────────

const TAB_LINKS: Record<Instrument, (s: SongData) => string> = {
  guitar: (s) =>
    `https://www.songsterr.com/?pattern=${encodeURIComponent(`${s.title} ${s.artist}`)}`,
  harmonica: (s) =>
    `https://www.harptabs.com/search.php?search_string=${encodeURIComponent(`${s.title} ${s.artist}`)}`,
  piano: (s) =>
    `https://www.musicnotes.com/search/go?w=${encodeURIComponent(`${s.title} ${s.artist}`)}`,
};

function TabsPanel({ songData }: { songData: SongData }) {
  const externalLink = TAB_LINKS[songData.instrument]?.(songData) ?? '#';
  const labels: Record<Instrument, string> = { guitar: 'Songsterr', harmonica: 'HarpTabs', piano: 'Musicnotes' };

  if (songData.instrument === 'guitar' && songData.songsterrId) {
    return (
      <div>
        <p className="text-gray-400 text-sm mb-3 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-400" />
          Interactive guitar tab via Songsterr
        </p>
        <iframe
          src={`https://www.songsterr.com/a/wsa/iframe#${songData.songsterrId}a0`}
          className="w-full rounded-xl border border-gray-700"
          style={{ height: 520 }}
          title="Guitar Tab — Songsterr"
        />
        <a href={externalLink} target="_blank" rel="noopener noreferrer"
          className="mt-3 flex items-center gap-1.5 text-xs text-gray-500 hover:text-indigo-400 transition-colors">
          <ExternalLink className="w-3 h-3" />Browse more on Songsterr
        </a>
      </div>
    );
  }

  if (songData.tabUrl) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="w-10 h-10 text-green-400 mx-auto mb-3" />
        <p className="text-gray-300 font-medium mb-4">Tab found on {labels[songData.instrument]}</p>
        <a href={songData.tabUrl} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold transition-colors">
          <ExternalLink className="w-4 h-4" />Open Tab
        </a>
      </div>
    );
  }

  return (
    <div className="text-center py-12">
      <Music className="w-12 h-12 mx-auto mb-4 text-gray-700" />
      <p className="text-gray-400 mb-2 font-medium">No embedded tab found.</p>
      <a href={externalLink} target="_blank" rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl border border-gray-700 font-medium text-sm transition-all">
        <ExternalLink className="w-4 h-4" />Search on {labels[songData.instrument]}
      </a>
    </div>
  );
}

// ─── main export ──────────────────────────────────────────────────────────────

type Tab = 'lyrics' | 'tabs';

export default function LyricsWithChords({
  songData,
  scrollContainerRef,
}: {
  songData: SongData;
  scrollContainerRef: React.RefObject<HTMLElement | null>;
}) {
  const [activeTab, setActiveTab] = useState<Tab>('lyrics');
  const [autoScroll, setAutoScroll] = useState(false);
  const [scrollSpeed, setScrollSpeed] = useState(3);
  const [fontSize, setFontSize] = useState(14);

  const scrollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-scroll: drive the ref-attached scroll container
  const startScroll = useCallback(() => {
    scrollIntervalRef.current = setInterval(() => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop += scrollSpeed * 0.6;
      }
    }, 60);
  }, [scrollSpeed, scrollContainerRef]);

  const stopScroll = useCallback(() => {
    if (scrollIntervalRef.current) {
      clearInterval(scrollIntervalRef.current);
      scrollIntervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (autoScroll) {
      startScroll();
    } else {
      stopScroll();
    }
    return stopScroll;
  }, [autoScroll, scrollSpeed, startScroll, stopScroll]);

  // Stop scroll when user manually scrolls
  useEffect(() => {
    const el = scrollContainerRef.current;
    const onWheel = () => { if (autoScroll) setAutoScroll(false); };
    el?.addEventListener('wheel', onWheel, { passive: true });
    return () => el?.removeEventListener('wheel', onWheel);
  }, [autoScroll, scrollContainerRef]);

  const isHarmonica = songData.instrument === 'harmonica';

  // Harmonica tabs use blow/draw numbers (e.g. "6 -6 7") — not chord letter notation.
  const hasHarmonicaNotation = isHarmonica && !!(songData.chords && (() => {
    const notationLines = songData.chords.split('\n').filter((l) => {
      const t = l.trim();
      return t.length >= 2 && /^[\d +\-]+$/.test(t) && /\d/.test(t);
    });
    return notationLines.length >= 3;
  })());

  const hasChordAnnotations = !isHarmonica && !!(
    songData.chords &&
    (songData.chords.includes('[') || isChordOnlyLine(songData.chords.split('\n')[0] ?? ''))
  );
  const displayContent = songData.chords || songData.lyrics || '';
  const instLabel = songData.instrument.charAt(0).toUpperCase() + songData.instrument.slice(1);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Tab nav */}
      <div className="flex gap-1 mb-0 bg-gray-900 rounded-t-2xl p-1 w-fit border-b-0">
        {([
          { id: 'lyrics', label: 'Lyrics & Chords', icon: BookOpen },
          { id: 'tabs', label: `${instLabel} Tabs`, icon: Music },
        ] as { id: Tab; label: string; icon: React.ElementType }[]).map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 ${
              activeTab === t.id ? 'text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {activeTab === t.id && (
              <motion.div layoutId="tab-bg"
                className="absolute inset-0 bg-indigo-600 rounded-xl"
                transition={{ type: 'spring', stiffness: 400, damping: 35 }}
              />
            )}
            <t.icon className="w-4 h-4 relative z-10" />
            <span className="relative z-10">{t.label}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={activeTab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }} transition={{ duration: 0.18 }}
          className="bg-gray-900 rounded-b-2xl rounded-tr-2xl overflow-hidden">

          {/* Practice controls bar — only on lyrics tab */}
          {activeTab === 'lyrics' && (
            <PracticeControls
              autoScroll={autoScroll}
              onAutoScrollChange={setAutoScroll}
              scrollSpeed={scrollSpeed}
              onScrollSpeedChange={setScrollSpeed}
              fontSize={fontSize}
              onFontSizeChange={setFontSize}
            />
          )}

          <div className="p-5">
            {activeTab === 'lyrics' ? (
              <>
                {/* Source badge */}
                <div className="flex items-center gap-2 mb-4 text-xs">
                  {hasHarmonicaNotation ? (
                    <span className="flex items-center gap-1.5 text-green-400">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Harmonica tab found — blow/draw numbers shown below
                    </span>
                  ) : hasChordAnnotations ? (
                    <span className="flex items-center gap-1.5 text-green-400">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Chord annotations found — chords highlighted above lyrics
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-yellow-500">
                      <Info className="w-3.5 h-3.5" />
                      {isHarmonica ? 'No harmonica tab found — showing lyrics only' : 'Plain lyrics only — chord data unavailable'}
                    </span>
                  )}
                  {hasChordAnnotations && (
                    <span className="text-gray-600">
                      •{' '}
                      <span className="bg-indigo-900/50 text-blue-300 font-bold rounded px-0.5 border border-indigo-700/40">
                        Am
                      </span>{' '}
                      = chord marker
                    </span>
                  )}
                </div>

                <ChordSheet content={displayContent} fontSize={fontSize} instrument={songData.instrument} />
              </>
            ) : (
              <TabsPanel songData={songData} />
            )}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
