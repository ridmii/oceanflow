// src/ui/Legend.tsx
// Speed color scale legend, bottom-left.

import { memo } from 'react';
import { LEGEND_GRADIENT, LEGEND_TICKS } from '../lib/colorScale';

const Legend = memo(function Legend() {
  return (
    <div
      id="legend-panel"
      className="glass-panel px-4 py-3 flex flex-col gap-1.5"
      role="region"
      aria-label="Speed color legend"
    >
      <span className="text-[11px] text-white/50 font-medium tracking-wide uppercase">
        Drift Speed
      </span>

      {/* Gradient bar */}
      <div
        className="h-3 rounded"
        style={{ background: LEGEND_GRADIENT }}
        aria-hidden="true"
      />

      {/* Tick labels */}
      <div className="flex justify-between tabular text-[10px] text-white/50">
        {LEGEND_TICKS.map((v) => (
          <span key={v}>{v.toFixed(1)}</span>
        ))}
      </div>

      <div className="text-[10px] text-white/30 flex justify-between">
        <span>m/s</span>
        <span className="italic">Simulated, not measured.</span>
      </div>
    </div>
  );
});

export default Legend;
