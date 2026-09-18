import React, { useState, useEffect } from 'react';

/**
 * LabSparkline Component
 * 
 * Renders longitudinal lab trend sparklines with:
 * - Color-coded reference range bands (green = normal, red/amber = abnormal)
 * - Excluded point markers for unit mismatches
 * - Out-of-range pulse alert on the latest value
 * - Click-to-explain / Click-to-source triggers
 */
export default function LabSparkline({
  patientId,
  testQuery = '',
  initialTrends = null,
  onExplainLab = null,
  onSourceClick = null,
}) {
  const [trends, setTrends] = useState(initialTrends);
  const [loading, setLoading] = useState(!initialTrends && !!patientId);
  const [error, setError] = useState(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  useEffect(() => {
    if (initialTrends) {
      setTrends(initialTrends);
      return;
    }
    if (!patientId) return;

    let isMounted = true;
    setLoading(true);
    const url = `/api/visualization/lab-trends/${patientId}${testQuery ? `?test=${encodeURIComponent(testQuery)}` : ''}`;

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setTrends(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [patientId, testQuery, initialTrends]);

  if (loading) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-center space-x-3 text-slate-400">
        <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Loading lab trends...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-950/30 border border-rose-800/40 rounded-xl p-3 text-xs text-rose-300">
        Could not load lab trends: {error}
      </div>
    );
  }

  if (!trends || !trends.tracked_labs || trends.tracked_labs.length === 0) {
    return (
      <div className="bg-slate-900/40 border border-slate-800/60 rounded-xl p-4 text-center text-slate-500 text-xs">
        No longitudinal lab history available yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          Longitudinal Lab Trends & Normal Zones
        </h3>
        <span className="text-xs text-slate-400">
          Green band indicates safe reference range
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {trends.tracked_labs.map((lab) => (
          <SingleLabChart
            key={lab.test_key}
            lab={lab}
            hoveredPoint={hoveredPoint}
            setHoveredPoint={setHoveredPoint}
            onExplainLab={onExplainLab}
            onSourceClick={onSourceClick}
          />
        ))}
      </div>
    </div>
  );
}

function SingleLabChart({ lab, hoveredPoint, setHoveredPoint, onExplainLab, onSourceClick }) {
  const points = lab.points || [];
  const validPoints = points.filter((p) => !p.is_excluded && p.value !== null);
  const excludedPoints = points.filter((p) => p.is_excluded);
  const ref = lab.reference_range || {};
  const hasRefRange = ref.low !== null && ref.high !== null;

  // Compute coordinate domain
  const values = validPoints.map((p) => p.value);
  if (hasRefRange) {
    values.push(ref.low, ref.high);
  }

  const minVal = values.length ? Math.min(...values) : 0;
  const maxVal = values.length ? Math.max(...values) : 10;
  const padding = (maxVal - minVal) * 0.2 || 2;
  const yDomainMin = Math.max(0, minVal - padding);
  const yDomainMax = maxVal + padding;

  const width = 280;
  const height = 100;
  const padX = 24;
  const padY = 16;
  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const scaleY = (val) => {
    if (yDomainMax === yDomainMin) return height / 2;
    return padY + chartH - ((val - yDomainMin) / (yDomainMax - yDomainMin)) * chartH;
  };

  const scaleX = (index, total) => {
    if (total <= 1) return width / 2;
    return padX + (index / (total - 1)) * chartW;
  };

  // Normal band coordinates
  const bandTop = hasRefRange ? scaleY(ref.high) : 0;
  const bandBottom = hasRefRange ? scaleY(ref.low) : 0;
  const bandHeight = Math.max(0, bandBottom - bandTop);

  // Line path for valid points
  const validCoords = validPoints.map((p, idx) => ({
    x: scaleX(idx, validPoints.length),
    y: scaleY(p.value),
    point: p,
  }));

  const pathD = validCoords.length > 0
    ? validCoords.reduce((acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`, '')
    : '';

  const latestPoint = validPoints[validPoints.length - 1];
  const isLatestAbnormal = latestPoint && latestPoint.status !== 'normal';

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 hover:border-slate-700 transition flex flex-col justify-between relative shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-100 uppercase tracking-wide">
              {lab.test_name}
            </span>
            {isLatestAbnormal && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-400 flex items-center gap-1">
            <span>Standard Unit: <strong className="text-slate-300">{lab.standard_unit}</strong></span>
            {hasRefRange && (
              <span className="text-slate-500">
                ({ref.low} - {ref.high})
              </span>
            )}
          </div>
        </div>

        {/* Latest Value Badge */}
        {latestPoint ? (
          <div className="text-right">
            <div className={`text-base font-extrabold ${
              latestPoint.status === 'high'
                ? 'text-rose-400'
                : latestPoint.status === 'low'
                ? 'text-amber-400'
                : 'text-emerald-400'
            }`}>
              {latestPoint.value} <span className="text-[10px] font-normal text-slate-400">{latestPoint.unit || lab.standard_unit}</span>
            </div>
            <span className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-semibold ${
              latestPoint.status === 'high'
                ? 'bg-rose-950/60 text-rose-300 border border-rose-800/50'
                : latestPoint.status === 'low'
                ? 'bg-amber-950/60 text-amber-300 border border-amber-800/50'
                : 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/50'
            }`}>
              {latestPoint.status}
            </span>
          </div>
        ) : (
          <span className="text-[10px] text-slate-500 italic">No values</span>
        )}
      </div>

      {/* SVG Sparkline */}
      <div className="relative my-1 bg-slate-950/60 rounded-lg p-1 border border-slate-900">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-24 overflow-visible"
        >
          {/* Reference range normal zone band */}
          {hasRefRange && (
            <g>
              <rect
                x={padX}
                y={bandTop}
                width={chartW}
                height={bandHeight}
                fill="rgba(16, 185, 129, 0.12)"
                stroke="rgba(16, 185, 129, 0.25)"
                strokeDasharray="2 2"
                strokeWidth="0.8"
              />
              {/* Reference high/low text */}
              <text
                x={padX + 2}
                y={bandTop - 2}
                fill="#6ee7b7"
                fontSize="8"
                opacity="0.7"
              >
                Max {ref.high}
              </text>
              <text
                x={padX + 2}
                y={bandBottom + 7}
                fill="#6ee7b7"
                fontSize="8"
                opacity="0.7"
              >
                Min {ref.low}
              </text>
            </g>
          )}

          {/* Sparkline Path */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke="#94a3b8"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Valid Data Points */}
          {validCoords.map((c, i) => {
            const p = c.point;
            const isHovered = hoveredPoint && hoveredPoint.id === p.id;
            const fillColor =
              p.status === 'high' ? '#f43f5e' : p.status === 'low' ? '#f59e0b' : '#10b981';

            return (
              <g key={p.id || i}>
                <circle
                  cx={c.x}
                  cy={c.y}
                  r={isHovered ? 5.5 : 3.5}
                  fill={fillColor}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                  className="cursor-pointer transition-all duration-150 hover:opacity-90"
                  onMouseEnter={() => setHoveredPoint(p)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  onClick={() => onSourceClick && p.source_ref && onSourceClick(p.source_ref)}
                />
              </g>
            );
          })}

          {/* Excluded Points (Unit mismatch) */}
          {excludedPoints.map((p, idx) => {
            // Position near the right or spaced out
            const xPos = width - padX - (idx + 1) * 14;
            const yPos = padY + 6;
            return (
              <g
                key={p.id || `ex-${idx}`}
                className="cursor-help"
                onMouseEnter={() => setHoveredPoint(p)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <circle
                  cx={xPos}
                  cy={yPos}
                  r="4"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  strokeDasharray="2 1"
                />
                <text
                  x={xPos}
                  y={yPos + 3}
                  textAnchor="middle"
                  fill="#ef4444"
                  fontSize="7"
                  fontWeight="bold"
                >
                  !
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredPoint && (
          <div className="absolute top-0 right-0 bg-slate-800/95 border border-slate-700 text-slate-200 text-[11px] p-2 rounded shadow-lg backdrop-blur-md z-10 max-w-[200px] pointer-events-none">
            <div className="font-semibold text-white">
              {hoveredPoint.date || 'Undated'}
            </div>
            {hoveredPoint.is_excluded ? (
              <div className="text-rose-400 font-medium mt-0.5">
                {hoveredPoint.exclusion_reason || 'Excluded from trend due to unit mismatch'}
              </div>
            ) : (
              <div className="flex items-center justify-between gap-2 mt-0.5">
                <span>Value:</span>
                <span className={`font-mono font-bold ${
                  hoveredPoint.status === 'high'
                    ? 'text-rose-400'
                    : hoveredPoint.status === 'low'
                    ? 'text-amber-400'
                    : 'text-emerald-400'
                }`}>
                  {hoveredPoint.value} {hoveredPoint.unit || lab.standard_unit}
                </span>
              </div>
            )}
            <div className="text-[10px] text-slate-400 mt-1">
              Source: {hoveredPoint.source_label || 'Lab Document'}
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions: Explain Lab & Click-To-Source */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-[11px]">
        <span className="text-slate-500">
          {validPoints.length} point{validPoints.length === 1 ? '' : 's'} recorded
        </span>
        <div className="flex items-center gap-2">
          {latestPoint && latestPoint.source_ref && (
            <button
              onClick={() => onSourceClick && onSourceClick(latestPoint.source_ref)}
              className="text-slate-400 hover:text-slate-200 underline hover:no-underline transition"
              title="View source document for latest lab test"
            >
              Source
            </button>
          )}
          {onExplainLab && (
            <button
              onClick={() => onExplainLab(latestPoint || { test_name: lab.test_name, value: null })}
              className="px-2 py-0.5 bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 rounded transition font-medium flex items-center gap-1"
            >
              <span>Explain</span>
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
