'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { SongData } from '@/lib/types';

interface Props {
  songData: SongData;
}

const INSTRUMENT_META: Record<string, { emoji: string; color: string }> = {
  guitar: { emoji: '🎸', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' },
  harmonica: { emoji: '🎼', color: 'text-sky-400 bg-sky-500/10 border-sky-500/30' },
  piano: { emoji: '🎹', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
};

export default function DashboardNav({ songData }: Props) {
  const meta = INSTRUMENT_META[songData.instrument] || { emoji: '🎵', color: 'text-gray-400 bg-gray-800 border-gray-700' };

  return (
    <nav className="sticky top-0 z-40 bg-gray-950/90 backdrop-blur border-b border-gray-800 px-4 py-3">
      <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/"
            className="p-2 rounded-lg text-gray-500 hover:text-white hover:bg-gray-800 transition-all shrink-0"
            title="Back to search"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <h1 className="text-white font-bold text-base truncate leading-tight">
              {songData.title || songData.query}
            </h1>
            {songData.artist && (
              <p className="text-gray-400 text-xs truncate">{songData.artist}</p>
            )}
          </div>
        </div>
        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold shrink-0 ${meta.color}`}>
          <span>{meta.emoji}</span>
          <span className="capitalize">{songData.instrument}</span>
        </div>
      </div>
    </nav>
  );
}
