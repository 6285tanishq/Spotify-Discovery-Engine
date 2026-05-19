'use client';

import { motion } from 'framer-motion';

interface Props {
  query: string;
  instrument: string;
}

const INSTRUMENT_LABELS: Record<string, { label: string; emoji: string }> = {
  guitar: { label: 'guitar tabs', emoji: '🎸' },
  harmonica: { label: 'harmonica numbers', emoji: '🎼' },
  piano: { label: 'piano chords', emoji: '🎹' },
};

const STEPS = ['Finding audio...', 'Loading lyrics...', 'Fetching tabs...'];

const BAR_COUNT = 28;

export default function WaveformLoader({ query, instrument }: Props) {
  const inst = INSTRUMENT_LABELS[instrument] || { label: 'tabs', emoji: '🎵' };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center p-8 relative overflow-hidden">
      {/* background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-indigo-900/20 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="relative z-10 text-center"
      >
        {/* Waveform animation */}
        <div className="flex items-center justify-center gap-[3px] h-20 mb-8">
          {Array.from({ length: BAR_COUNT }).map((_, i) => (
            <motion.div
              key={i}
              className="w-[5px] rounded-full origin-bottom"
              style={{
                background: `hsl(${240 + (i / BAR_COUNT) * 60}, 80%, 65%)`,
              }}
              animate={{
                scaleY: [0.15, 1, 0.3, 0.85, 0.2, 0.95, 0.4, 0.15],
              }}
              transition={{
                duration: 1.4 + (i % 4) * 0.1,
                delay: (i / BAR_COUNT) * 0.7,
                repeat: Infinity,
                repeatType: 'mirror',
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>

        <motion.h2
          animate={{ opacity: [0.8, 1, 0.8] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-3xl font-bold text-white mb-2"
        >
          Analyzing Track
        </motion.h2>

        <p className="text-indigo-300 font-semibold text-lg mb-1">"{query}"</p>
        <p className="text-gray-500 text-sm mb-8">
          {inst.emoji} Fetching {inst.label}, lyrics &amp; audio…
        </p>

        {/* Step indicators */}
        <div className="flex gap-3 justify-center flex-wrap">
          {STEPS.map((step, i) => (
            <motion.span
              key={step}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{
                duration: 1.8,
                delay: i * 0.6,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800/80 text-gray-400 rounded-full text-xs border border-gray-700"
            >
              <span
                className="w-1.5 h-1.5 rounded-full bg-indigo-400 inline-block"
                style={{ boxShadow: '0 0 6px #818cf8' }}
              />
              {step}
            </motion.span>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
