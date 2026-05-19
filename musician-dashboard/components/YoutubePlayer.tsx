'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Music2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  videoId?: string;
  title?: string;
  artist?: string;
}

export default function YoutubePlayer({ videoId, title, artist }: Props) {
  const [expanded, setExpanded] = useState(true);

  if (!videoId) {
    return (
      <div className="bg-gray-900/95 backdrop-blur border-t border-gray-800 px-4 py-3 flex items-center gap-3 text-gray-500 text-sm">
        <Music2 className="w-4 h-4 shrink-0" />
        Audio unavailable — try searching on{' '}
        <a
          href={`https://www.youtube.com/results?search_query=${encodeURIComponent(title || '')}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-400 underline"
        >
          YouTube
        </a>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/95 backdrop-blur border-t border-gray-800">
      {/* Control bar */}
      <div className="flex items-center justify-between px-4 py-2.5">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
            <svg className="w-3 h-3 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-white text-sm font-semibold truncate max-w-[250px] sm:max-w-[450px]">
              {title || 'Now Playing'}
            </p>
            {artist && <p className="text-gray-500 text-xs truncate">{artist}</p>}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <a
            href={`https://www.youtube.com/watch?v=${videoId}`}
            target="_blank"
            rel="noopener noreferrer"
            title="Open on YouTube"
            className="text-gray-500 hover:text-white transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
          <button
            onClick={() => setExpanded(!expanded)}
            title={expanded ? 'Collapse player' : 'Expand player'}
            className="text-gray-500 hover:text-white transition-colors"
          >
            {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* YouTube iframe */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="player"
            initial={{ height: 0 }}
            animate={{ height: 220 }}
            exit={{ height: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <iframe
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1`}
              className="w-full h-[220px]"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              title={title || 'Music Player'}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
