'use client';

import { Play, Pause, Minus, Plus, Gauge } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  autoScroll: boolean;
  onAutoScrollChange: (v: boolean) => void;
  scrollSpeed: number;
  onScrollSpeedChange: (v: number) => void;
  fontSize: number;
  onFontSizeChange: (v: number) => void;
}

const MIN_FONT = 11;
const MAX_FONT = 26;
const MIN_SPEED = 1;
const MAX_SPEED = 10;

export default function PracticeControls({
  autoScroll,
  onAutoScrollChange,
  scrollSpeed,
  onScrollSpeedChange,
  fontSize,
  onFontSizeChange,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-gray-950/80 backdrop-blur border-b border-gray-800/60 rounded-t-2xl select-none">
      {/* ── Auto-Scroll ── */}
      <div className="flex items-center gap-2">
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => onAutoScrollChange(!autoScroll)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            autoScroll
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
          }`}
        >
          {autoScroll ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          Auto-Scroll
          {autoScroll && (
            <motion.span
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1.4, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full bg-indigo-300 ml-0.5"
            />
          )}
        </motion.button>

        {/* Speed slider — only shown while active */}
        <div
          className={`flex items-center gap-2 transition-all duration-200 ${
            autoScroll ? 'opacity-100' : 'opacity-40 pointer-events-none'
          }`}
        >
          <Gauge className="w-3 h-3 text-gray-500 shrink-0" />
          <input
            type="range"
            min={MIN_SPEED}
            max={MAX_SPEED}
            step={1}
            value={scrollSpeed}
            onChange={(e) => onScrollSpeedChange(Number(e.target.value))}
            className="w-24 h-1 accent-indigo-500 cursor-pointer"
            title={`Scroll speed: ${scrollSpeed}`}
          />
          <span className="text-[10px] text-gray-500 w-4 text-right">{scrollSpeed}</span>
        </div>
      </div>

      <div className="h-4 w-px bg-gray-800 hidden sm:block" />

      {/* ── Font Size ── */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-gray-500 uppercase tracking-wide mr-1">Size</span>
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={() => onFontSizeChange(Math.max(MIN_FONT, fontSize - 1))}
          disabled={fontSize <= MIN_FONT}
          className="w-7 h-7 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-300 transition-colors"
          title="Decrease font size"
        >
          <Minus className="w-3 h-3" />
        </motion.button>

        <span className="text-xs text-gray-400 w-8 text-center tabular-nums">
          {fontSize}px
        </span>

        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={() => onFontSizeChange(Math.min(MAX_FONT, fontSize + 1))}
          disabled={fontSize >= MAX_FONT}
          className="w-7 h-7 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed text-gray-300 transition-colors"
          title="Increase font size"
        >
          <Plus className="w-3 h-3" />
        </motion.button>
      </div>
    </div>
  );
}
