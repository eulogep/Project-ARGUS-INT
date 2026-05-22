// ==============================================================================
// Project ARGUS-INT - Temporal Slider Component (4D Graph Travel)
// Lets the operator restrict the visible graph to a dynamic time-frame
// ==============================================================================

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useAppStore } from '@/lib/store';

export function TemporalSlider() {
  const nodes = useAppStore((s) => s.nodes);
  const graphFilter = useAppStore((s) => s.graphFilter);
  const setGraphFilter = useAppStore((s) => s.setGraphFilter);

  // Compute absolute time boundaries of the active graph
  const timeBoundaries = useMemo(() => {
    const timestamps = nodes
      .map((n) => (n.first_seen ? new Date(n.first_seen).getTime() : null))
      .filter((t): t is number => t !== null);

    if (timestamps.length === 0) {
      const now = Date.now();
      return { min: now - 3600000 * 24, max: now }; // default 24h range
    }

    return {
      min: Math.min(...timestamps),
      max: Math.max(...timestamps),
    };
  }, [nodes]);

  const [sliderVal, setSliderVal] = useState<number>(timeBoundaries.max);

  // Reset local state if boundaries shift
  useEffect(() => {
    setSliderVal(timeBoundaries.max);
    setGraphFilter({ timeRange: null });
  }, [timeBoundaries, setGraphFilter]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setSliderVal(val);

    // Filter nodes from boundary min up to slider selected timestamp
    setGraphFilter({
      timeRange: [timeBoundaries.min, val],
    });
  };

  const formatDate = (ts: number) => {
    return new Date(ts).toISOString().replace('T', ' ').substr(0, 19) + ' Z';
  };

  return (
    <div className="temporal-slider animate-in">
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', color: 'var(--accent-primary)' }}>
        <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="16" height="16">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>4D Time Travel</span>
      </div>

      <input
        type="range"
        min={timeBoundaries.min}
        max={timeBoundaries.max}
        value={sliderVal}
        onChange={handleSliderChange}
      />

      <div className="temporal-label">
        {formatDate(sliderVal)}
      </div>
    </div>
  );
}
export default TemporalSlider;
