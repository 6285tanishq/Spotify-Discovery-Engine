'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Music2, ArrowRight, Disc3 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const INSTRUMENT_LABELS: Record<string, string> = {
  guitar: '🎸 Guitar',
  harmonica: '🎼 Harmonica',
  piano: '🎹 Piano',
};

const EXAMPLES = [
  'Wonderwall - Oasis',
  'Hotel California - Eagles',
  'Bohemian Rhapsody - Queen',
  'Sweet Home Chicago - Robert Johnson',
];

interface Suggestion {
  title: string;
  artist: string;
  query: string;
}

interface Props {
  instrument: string;
}

export default function SearchBar({ instrument }: Props) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const navigate = (q: string, title?: string, artist?: string) => {
    if (!q.trim()) return;
    const params = new URLSearchParams({ q: q.trim(), instrument });
    if (title) params.set('title', title);
    if (artist) params.set('artist', artist);
    router.push(`/dashboard?${params.toString()}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    navigate(query);
  };

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (val.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const res = await fetch(`/api/suggestions?q=${encodeURIComponent(val.trim())}`);
        const data = await res.json();
        setSuggestions(data.suggestions ?? []);
        setShowSuggestions((data.suggestions?.length ?? 0) > 0);
      } catch {
        setSuggestions([]);
      } finally {
        setLoadingSuggestions(false);
      }
    }, 300);
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  const fillExample = (ex: string) => {
    setQuery(ex);
    setSuggestions([]);
    setShowSuggestions(false);
  };

  return (
    <div>
      <div ref={containerRef} className="relative">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center bg-gray-900 border-2 border-gray-700 rounded-2xl overflow-hidden focus-within:border-indigo-500 transition-colors duration-200">
            <div className="pl-4 text-gray-500 shrink-0">
              {loadingSuggestions
                ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}><Disc3 className="w-5 h-5 text-indigo-400" /></motion.div>
                : <Music2 className="w-5 h-5" />
              }
            </div>
            <input
              type="text"
              value={query}
              onChange={handleQueryChange}
              onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
              placeholder={`Song Name - Artist (e.g. ${EXAMPLES[0]})`}
              autoFocus
              autoComplete="off"
              className="flex-1 bg-transparent py-4 px-4 text-white placeholder-gray-600 focus:outline-none text-base"
            />
            <motion.button
              type="submit"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={!query.trim()}
              className="m-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-xl font-semibold text-sm flex items-center gap-2 transition-colors duration-200"
            >
              <Search className="w-4 h-4" />
              Analyze
              <ArrowRight className="w-4 h-4" />
            </motion.button>
          </div>
        </form>

        {/* Autocomplete dropdown */}
        <AnimatePresence>
          {showSuggestions && suggestions.length > 0 && (
            <motion.div
              key="suggestions"
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full left-0 right-0 mt-2 z-50 bg-gray-900/95 backdrop-blur-md border border-gray-700/80 rounded-2xl overflow-hidden shadow-2xl shadow-black/40"
            >
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault(); // keep input focused
                    setQuery(s.query);
                    setShowSuggestions(false);
                    // Pass clean title/artist as explicit params so the dashboard
                    // doesn't have to re-parse a potentially noisy query string
                    navigate(s.query, s.title, s.artist);
                  }}
                  className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-indigo-600/20 transition-colors duration-100 border-b border-gray-800/60 last:border-0 group"
                >
                  <div className="w-7 h-7 rounded-lg bg-gray-800 group-hover:bg-indigo-600/30 flex items-center justify-center shrink-0 transition-colors">
                    <Music2 className="w-3.5 h-3.5 text-gray-500 group-hover:text-indigo-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-white font-medium truncate">{s.title}</div>
                    {s.artist && (
                      <div className="text-xs text-gray-500 truncate">{s.artist}</div>
                    )}
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-indigo-400 shrink-0 transition-colors" />
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-4">
        <p className="text-center text-xs text-gray-600 mb-2">
          Searching for {INSTRUMENT_LABELS[instrument] || instrument} tabs. Try an example:
        </p>
        <div className="flex flex-wrap gap-2 justify-center">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => fillExample(ex)}
              className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 rounded-full transition-colors duration-150 border border-gray-700 hover:border-gray-600"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
