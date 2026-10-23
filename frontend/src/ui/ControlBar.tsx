// src/ui/ControlBar.tsx
// Wrapper around Timeline. Positioned bottom-center.
// memo'd to avoid re-renders from parent.

import { memo } from 'react';
import Timeline from './Timeline';
import { useQueryStore } from '../store/queryStore';

const ControlBar = memo(function ControlBar() {
  const point = useQueryStore((state) => state.point);
  const clearQuery = useQueryStore((state) => state.clearQuery);

  return (
    <div
      id="control-bar"
      className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-xl
                 z-10 pointer-events-auto flex flex-col items-center gap-4"
    >
      <Timeline />
      {point && (
        <button
          onClick={clearQuery}
          className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-full shadow-lg border border-slate-600 transition-colors"
        >
          Clear Query
        </button>
      )}
    </div>
  );
});

export default ControlBar;
