import { useEffect, useState } from 'react';
import { useQueryStore } from '../store/queryStore';
import { useParticleData } from '../hooks/useParticleData';

interface FluxSource {
  sourceId: string;
  name: string;
  passes: number;
  particles: number;
}

interface FluxTimeSeries {
  frameIndex: number;
  cumulativePasses: number;
}

interface FluxResponse {
  runId: string;
  query: { lon: number; lat: number; radiusKm: number };
  totalPasses: number;
  uniqueParticles: number;
  particleCount: number;
  fraction: number;
  estimatedTons: number;
  bySource: FluxSource[];
  timeSeries: FluxTimeSeries[];
}

export default function QueryPanel() {
  const point = useQueryStore((state) => state.point);
  const radiusKm = useQueryStore((state) => state.radiusKm);
  const setRadius = useQueryStore((state) => state.setRadius);
  const clearQuery = useQueryStore((state) => state.clearQuery);
  const { source } = useParticleData();

  const [data, setData] = useState<FluxResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!point) return;

    let cancel = false;
    const runId = (source as any).runId || 'minimal';

    const fetchFlux = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/runs/${runId}/flux?lon=${point.lon}&lat=${point.lat}&radius_km=${radiusKm}`);
        if (!res.ok) throw new Error(res.statusText);
        const json = await res.json();
        if (!cancel) {
          setData(json);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancel) setLoading(false);
      }
    };

    const timer = setTimeout(fetchFlux, 300);
    return () => {
      cancel = true;
      clearTimeout(timer);
    };
  }, [point, radiusKm, source]);

  if (!point) return null;

  return (
    <div className="absolute right-4 top-4 w-80 bg-slate-900/90 text-white p-4 rounded-lg shadow-xl border border-slate-700 pointer-events-auto backdrop-blur-sm z-50">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold">Location Analysis</h3>
        <button onClick={clearQuery} className="text-gray-400 hover:text-white transition-colors">
          ✕
        </button>
      </div>

      <div className="text-sm text-gray-300 mb-4">
        {Math.abs(point.lon).toFixed(1)}°{point.lon >= 0 ? 'E' : 'W'}, {Math.abs(point.lat).toFixed(1)}°{point.lat >= 0 ? 'N' : 'S'}
      </div>

      <div className="mb-4">
        <label className="text-sm block mb-1 text-gray-400">Radius: {radiusKm} km</label>
        <input 
          type="range" 
          min="10" 
          max="500" 
          step="10"
          value={radiusKm}
          onChange={(e) => setRadius(Number(e.target.value))}
          className="w-full accent-blue-500"
        />
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-400 animate-pulse">Computing flux...</div>
      ) : data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 text-sm bg-slate-800 p-2 rounded">
            <div className="text-gray-400">Total Passes</div>
            <div className="text-right font-mono">{data.totalPasses.toLocaleString()}</div>
            <div className="text-gray-400">Unique Particles</div>
            <div className="text-right font-mono">{data.uniqueParticles.toLocaleString()}</div>
            <div className="text-gray-400">Fraction</div>
            <div className="text-right font-mono">{(data.fraction * 100).toFixed(2)}%</div>
            <div className="text-gray-400">Estimated Tons</div>
            <div className="text-right font-mono">{data.estimatedTons.toFixed(1)} t</div>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-2 text-gray-300">Top Sources</h4>
            <div className="space-y-1">
              {data.bySource.slice(0, 5).map((src) => {
                const maxPasses = data.bySource[0]?.passes || 1;
                const width = Math.max(5, (src.passes / maxPasses) * 100);
                return (
                  <div key={src.sourceId} className="text-xs">
                    <div className="flex justify-between mb-1">
                      <span>{src.name}</span>
                      <span className="font-mono">{src.passes}</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-blue-500 h-full" style={{ width: `${width}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-1 text-gray-300">Cumulative Time Series</h4>
            <div className="flex items-end h-12 gap-[1px] bg-slate-800 p-1 rounded">
              {data.timeSeries.map((ts, idx) => {
                const max = Math.max(1, data.timeSeries[data.timeSeries.length - 1]?.cumulativePasses || 1);
                const height = Math.max(2, (ts.cumulativePasses / max) * 100);
                return (
                  <div 
                    key={idx} 
                    className="flex-1 bg-teal-500 rounded-t-sm opacity-80" 
                    style={{ height: `${height}%` }}
                  />
                );
              })}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
