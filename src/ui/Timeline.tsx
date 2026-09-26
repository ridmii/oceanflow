// src/ui/Timeline.tsx
// Bottom control bar: play/pause, speed, timeline scrubber, date readout.

import { memo, useCallback, useEffect, useRef } from 'react';
import { usePlaybackStore } from '../store/playbackStore';
import { useParticleData } from '../hooks/useParticleData';
import { frameToDateString } from '../lib/format';
import { usePrefersReducedMotion } from '../hooks/usePlayback';

const SPEED_OPTIONS = [0.5, 1, 2, 4] as const;

const Timeline = memo(function Timeline() {
  const isPlaying     = usePlaybackStore((s) => s.isPlaying);
  const speed         = usePlaybackStore((s) => s.speed);
  const currentFrame  = usePlaybackStore((s) => s.currentFrame);
  const frameCount    = usePlaybackStore((s) => s.frameCount);
  const setPlaying    = usePlaybackStore((s) => s.setPlaying);
  const setSpeed      = usePlaybackStore((s) => s.setSpeed);
  const seekToFrame   = usePlaybackStore((s) => s.seekToFrame);

  const { meta }      = useParticleData();
  const reducedMotion = usePrefersReducedMotion();
  const wasPlayingRef = useRef(false);

  // Apply reduced-motion default
  useEffect(() => {
    if (reducedMotion && speed > 0.5) setSpeed(0.5);
  }, [reducedMotion, speed, setSpeed]);

  const dateStr = meta
    ? frameToDateString(meta.startDate, currentFrame, meta.timeStepHours)
    : '—';

  const handleScrubStart = useCallback(() => {
    wasPlayingRef.current = isPlaying;
    setPlaying(false);
  }, [isPlaying, setPlaying]);

  const handleScrub = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      seekToFrame(Number(e.target.value));
    },
    [seekToFrame],
  );

  const handleScrubEnd = useCallback(() => {
    if (wasPlayingRef.current) setPlaying(true);
  }, [setPlaying]);

  const togglePlay = useCallback(() => setPlaying(!isPlaying), [isPlaying, setPlaying]);

  return (
    <div
      className="glass-panel px-5 py-3 flex flex-col gap-2 w-full max-w-2xl mx-auto"
      role="region"
      aria-label="Playback controls"
    >
      {/* Top row: play/pause, speed, date */}
      <div className="flex items-center gap-4">
        {/* Play/Pause */}
        <button
          id="btn-play-pause"
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          className="flex-shrink-0 w-9 h-9 rounded-full bg-white/10 hover:bg-white/20
                     flex items-center justify-center transition-colors duration-150
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#6ec6e8]"
        >
          {isPlaying ? (
            // Pause icon
            <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="currentColor">
              <rect x="3" y="2" width="4" height="12" rx="1" />
              <rect x="9" y="2" width="4" height="12" rx="1" />
            </svg>
          ) : (
            // Play icon
            <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4 2.5l9 5.5-9 5.5z" />
            </svg>
          )}
        </button>

        {/* Speed selector */}
        <div className="flex gap-1" role="group" aria-label="Playback speed">
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              id={`btn-speed-${s}`}
              onClick={() => setSpeed(s)}
              aria-pressed={speed === s}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors duration-100
                ${speed === s
                  ? 'bg-[#2e7fb8] text-white'
                  : 'bg-white/8 text-white/60 hover:bg-white/15 hover:text-white'
                }`}
            >
              {s}×
            </button>
          ))}
        </div>

        {/* Date readout */}
        <span className="tabular text-xs text-white/50 ml-auto flex-shrink-0">
          {dateStr}
        </span>
      </div>

      {/* Timeline scrubber */}
      <input
        id="timeline-scrubber"
        type="range"
        min={0}
        max={Math.max(0, frameCount - 1)}
        value={currentFrame}
        step={1}
        aria-label="Simulation timeline"
        aria-valuetext={dateStr}
        className="w-full"
        onMouseDown={handleScrubStart}
        onTouchStart={handleScrubStart}
        onChange={handleScrub}
        onMouseUp={handleScrubEnd}
        onTouchEnd={handleScrubEnd}
      />

      {/* Frame ticks */}
      <div className="flex justify-between text-[10px] text-white/25 tabular px-px">
        <span>Frame 0</span>
        <span>Frame {frameCount - 1}</span>
      </div>
    </div>
  );
});

export default Timeline;
