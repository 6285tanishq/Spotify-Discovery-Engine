'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import InstrumentSelector from '@/components/InstrumentSelector';
import SearchBar from '@/components/SearchBar';

export default function HomePage() {
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background radial gradients */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-900/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[300px] bg-purple-900/15 rounded-full blur-3xl" />
        <div className="absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-blue-900/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-3xl flex flex-col items-center">
        {/* Logo / Header */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="text-center mb-14"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <span className="text-5xl">🎵</span>
            <h1 className="text-5xl font-black tracking-tight">
              <span className="text-white">Music</span>
              <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Dash</span>
            </h1>
          </div>
          <p className="text-gray-400 text-lg font-medium">
            Search any song. Learn to play it. Instantly.
          </p>
          <div className="flex items-center justify-center gap-6 mt-4 text-sm text-gray-600">
            <span>🎸 Guitar tabs</span>
            <span>•</span>
            <span>🎵 Harmonica numbers</span>
            <span>•</span>
            <span>🎹 Piano chords</span>
          </div>
        </motion.div>

        {/* Step 1: Instrument Selector */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: 'easeOut' }}
          className="w-full"
        >
          <p className="text-center text-xs font-semibold text-gray-500 uppercase tracking-[0.2em] mb-5">
            Step 1 — Choose your instrument
          </p>
          <InstrumentSelector selected={selectedInstrument} onSelect={setSelectedInstrument} />
        </motion.div>

        {/* Step 2: Search bar — slides in after instrument selection */}
        <AnimatePresence mode="wait">
          {selectedInstrument && (
            <motion.div
              key="search"
              initial={{ opacity: 0, y: 24, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -12, height: 0 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              className="w-full mt-10 overflow-hidden"
            >
              <p className="text-center text-xs font-semibold text-gray-500 uppercase tracking-[0.2em] mb-5">
                Step 2 — Search a song
              </p>
              <SearchBar instrument={selectedInstrument} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
