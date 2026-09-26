// src/ui/ControlBar.tsx
// Wrapper around Timeline. Positioned bottom-center.
// memo'd to avoid re-renders from parent.

import { memo } from 'react';
import Timeline from './Timeline';

const ControlBar = memo(function ControlBar() {
  return (
    <div
      id="control-bar"
      className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-xl
                 z-10 pointer-events-auto"
    >
      <Timeline />
    </div>
  );
});

export default ControlBar;
