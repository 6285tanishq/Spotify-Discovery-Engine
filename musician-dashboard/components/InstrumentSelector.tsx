'use client';

import { motion } from 'framer-motion';

interface Props {
  selected: string | null;
  onSelect: (instrument: string) => void;
}

const instruments = [
  {
    id: 'guitar',
    name: 'Guitar',
    emoji: '🎸',
    tagline: 'Chords & Tabs',
    description: 'Full fretboard tablature, chord diagrams, and interactive tab player.',
    gradient: 'from-amber-500/20 to-orange-600/10',
    border: 'border-amber-500/60',
    glow: 'shadow-amber-500/20',
    badgeColor: 'bg-amber-500/20 text-amber-300',
  },
  {
    id: 'harmonica',
    name: 'Harmonica',
    emoji: '🎼',
    tagline: 'Blow / Draw Numbers',
    description: 'Numbered hole tabs with blow and draw notation for diatonic harmonica.',
    gradient: 'from-sky-500/20 to-cyan-600/10',
    border: 'border-sky-500/60',
    glow: 'shadow-sky-500/20',
    badgeColor: 'bg-sky-500/20 text-sky-300',
  },
  {
    id: 'piano',
    name: 'Piano',
    emoji: '🎹',
    tagline: 'Chord Charts',
    description: 'Chord names, voicings, and visual keyboard charts for every progression.',
    gradient: 'from-purple-500/20 to-pink-600/10',
    border: 'border-purple-500/60',
    glow: 'shadow-purple-500/20',
    badgeColor: 'bg-purple-500/20 text-purple-300',
  },
];

export default function InstrumentSelector({ selected, onSelect }: Props) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {instruments.map((inst, i) => (
        <motion.button
          key={inst.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 * i, duration: 0.4 }}
          whileHover={{ scale: 1.03, y: -2 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onSelect(inst.id)}
          className={`
            relative text-left rounded-2xl border-2 p-5 transition-all duration-300 cursor-pointer
            ${selected === inst.id
              ? `bg-gradient-to-br ${inst.gradient} ${inst.border} shadow-xl ${inst.glow}`
              : 'bg-gray-900/80 border-gray-800 hover:border-gray-600 hover:bg-gray-900'
            }
          `}
        >
          {selected === inst.id && (
            <motion.div
              layoutId="selected-ring"
              className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${inst.gradient}`}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            />
          )}

          <div className="relative z-10">
            <div className="text-4xl mb-3">{inst.emoji}</div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-bold text-white text-lg">{inst.name}</h3>
              {selected === inst.id && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="text-xs px-2 py-0.5 rounded-full bg-white/20 text-white font-semibold"
                >
                  Selected
                </motion.span>
              )}
            </div>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${inst.badgeColor}`}>
              {inst.tagline}
            </span>
            <p className="text-gray-400 text-xs mt-2 leading-relaxed">{inst.description}</p>
          </div>
        </motion.button>
      ))}
    </div>
  );
}
