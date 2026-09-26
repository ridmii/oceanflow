// src/ui/SourceFilter.tsx
// Top-right collapsible source filter panel.

import { memo, useState } from 'react';
import { useFilterStore } from '../store/filterStore';
import { useParticleData } from '../hooks/useParticleData';

const SourceFilter = memo(function SourceFilter() {
  const [collapsed, setCollapsed] = useState(false);
  const { meta } = useParticleData();
  const visibility     = useFilterStore((s) => s.visibility);
  const setSourceVisible = useFilterStore((s) => s.setSourceVisible);
  const setAllVisible    = useFilterStore((s) => s.setAllVisible);

  const sources = meta?.sources ?? [];
  const ids     = sources.map((s) => s.id);

  if (collapsed) {
    return (
      <button
        id="btn-filter-expand"
        onClick={() => setCollapsed(false)}
        aria-label="Expand source filter"
        className="glass-panel p-2 text-white/60 hover:text-white text-xs"
      >
        ⊞ Sources
      </button>
    );
  }

  return (
    <div
      id="source-filter-panel"
      className="glass-panel p-4 w-52 text-xs text-white/80 flex flex-col gap-2"
      role="region"
      aria-label="River source filter"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white/90 text-sm">Sources</span>
        <button
          id="btn-filter-collapse"
          onClick={() => setCollapsed(true)}
          aria-label="Collapse source filter"
          className="text-white/40 hover:text-white/80 text-base leading-none"
        >
          ×
        </button>
      </div>

      {/* All / None */}
      <div className="flex gap-2">
        <button
          id="btn-sources-all"
          onClick={() => setAllVisible(ids, true)}
          className="flex-1 bg-white/10 hover:bg-white/20 rounded py-1 transition-colors"
        >
          All
        </button>
        <button
          id="btn-sources-none"
          onClick={() => setAllVisible(ids, false)}
          className="flex-1 bg-white/10 hover:bg-white/20 rounded py-1 transition-colors"
        >
          None
        </button>
      </div>

      {/* Scrollable source list */}
      <div
        className="overflow-y-auto max-h-72 flex flex-col gap-1 pr-1"
        role="list"
        aria-label="River sources"
      >
        {sources.map((src) => (
          <label
            key={src.id}
            className="flex items-center gap-2 cursor-pointer hover:bg-white/5
                       rounded px-1 py-0.5 transition-colors"
            role="listitem"
          >
            <input
              type="checkbox"
              id={`source-${src.id}`}
              checked={visibility[src.id] ?? true}
              onChange={(e) => setSourceVisible(src.id, e.target.checked)}
              aria-label={`Toggle ${src.name}`}
            />
            {/* Color swatch */}
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ background: src.color }}
            />
            <span className="truncate">{src.name}</span>
            <span className="ml-auto text-white/30 tabular text-[10px]">
              {Math.round(src.intensity * 100)}%
            </span>
          </label>
        ))}
      </div>

      {sources.length === 0 && (
        <p className="text-white/30 text-[11px]">Loading sources…</p>
      )}
    </div>
  );
});

export default SourceFilter;
