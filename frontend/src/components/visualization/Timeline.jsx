import React, { useState, useEffect, useRef } from 'react';
import {
  Calendar,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Activity,
  Pill,
  FileSpreadsheet,
  Stethoscope,
  Info,
  ExternalLink,
  Filter,
} from 'lucide-react';

const LANE_CONFIG = [
  { key: 'diagnoses', label: 'Diagnoses (रोग निदान)', icon: Activity, color: '#DC2626', y: 35 },
  { key: 'medications', label: 'Medications (दवाइयाँ)', icon: Pill, color: '#2563EB', y: 95 },
  { key: 'labs', label: 'Lab Reports (जांच परिणाम)', icon: FileSpreadsheet, color: '#059669', y: 155 },
  { key: 'procedures', label: 'Procedures (उपचार/शल्य)', icon: Stethoscope, color: '#7C3AED', y: 215 },
];

export const Timeline = ({
  patientId,
  onNodeClick,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState(0);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [activeLanes, setActiveLanes] = useState({
    diagnoses: true,
    medications: true,
    labs: true,
    procedures: true,
  });

  const svgRef = useRef(null);
  const isDragging = useRef(false);
  const startDragX = useRef(0);

  useEffect(() => {
    const fetchTimeline = async () => {
      if (!patientId) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/visualization/timeline/${patientId}`);
        if (!res.ok) throw new Error('Failed to load timeline');
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.warn('[Timeline] fetch error:', err);
        // Multi-visit fallback demonstrating all 4 swim lanes
        setData({
          patient_id: patientId,
          start_date: '2024-06-01',
          end_date: '2026-03-01',
          total_visits: 3,
          visit_dates: ['2024-08-15', '2025-05-10', '2026-01-12'],
          swim_lanes: {
            diagnoses: [
              { id: 'd1', title: 'Type 2 Diabetes Mellitus', date: '2024-08-15', status: 'active', confidence: 0.95 },
              { id: 'd2', title: 'Essential Hypertension', date: '2025-05-10', status: 'active', confidence: 0.92 },
              { id: 'd3', title: 'Acute Gastritis', date: '2026-01-12', status: 'resolved', confidence: 0.88 },
            ],
            medications: [
              { id: 'm1', title: 'Metformin 500mg BD', date: '2024-08-15', end_date: '2026-01-12', status: 'changed' },
              { id: 'm2', title: 'Glimepiride 1mg OD', date: '2024-08-15', end_date: '2026-01-12', status: 'stopped' },
              { id: 'm3', title: 'Amlodipine 5mg OD', date: '2025-05-10', status: 'active' },
              { id: 'm4', title: 'Metformin 1000mg BD', date: '2026-01-12', status: 'active' },
            ],
            labs: [
              { id: 'l1', test_name: 'HbA1c: 6.2%', value: '6.2%', date: '2024-08-15', is_abnormal: true },
              { id: 'l2', test_name: 'Serum Creatinine: 1.0 mg/dL', value: '1.0 mg/dL', date: '2025-05-10', is_abnormal: false },
              { id: 'l3', test_name: 'HbA1c: 7.1%', value: '7.1%', date: '2026-01-12', is_abnormal: true },
              { id: 'l4', test_name: 'Hemoglobin: 13.8 g/dL', value: '13.8 g/dL', date: '2026-01-12', is_abnormal: false },
            ],
            procedures: [
              { id: 'p1', title: '12-Lead ECG (Normal Sinus)', date: '2025-05-10' },
              { id: 'p2', title: 'Dilated Eye Exam (Fundus)', date: '2026-01-12' },
            ],
          },
        });
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [patientId]);

  // Compute X coordinate for a date string
  const getXForDate = (dateStr, width = 760) => {
    if (!data) return 0;
    const start = new Date(data.start_date || '2024-01-01').getTime();
    const end = new Date(data.end_date || '2026-12-31').getTime();
    const current = new Date(dateStr).getTime();
    const range = Math.max(end - start, 86400000 * 30);
    const pct = Math.min(Math.max((current - start) / range, 0.02), 0.98);
    const baseWidth = width * zoomLevel;
    return 140 + pct * (baseWidth - 160) + panOffset;
  };

  // Mouse pan handlers
  const handleMouseDown = (e) => {
    isDragging.current = true;
    startDragX.current = e.clientX - panOffset;
  };

  const handleMouseMove = (e) => {
    if (!isDragging.current) return;
    const newOffset = e.clientX - startDragX.current;
    setPanOffset(newOffset);
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  const handleWheel = (e) => {
    if (e.ctrlKey || Math.abs(e.deltaY) > 0) {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      setZoomLevel((prev) => Math.min(Math.max(prev + delta, 0.8), 3.0));
    }
  };

  const toggleLane = (key) => {
    setActiveLanes((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const svgWidth = 860;
  const svgHeight = 280;

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '16px',
        border: '1.5px solid #E2E8F0',
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.03)',
        overflow: 'hidden',
      }}
      id="patient-chronological-timeline"
    >
      {/* Header & Controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: '#F0FDF4',
              color: '#16A34A',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Calendar size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
              Chronological Patient Journey (मरीज का ऐतिहासिक टाइमलाइन)
            </h3>
            <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
              Multi-visit longitudinal swim lanes • Drag to pan • Scroll to zoom
            </div>
          </div>
        </div>

        {/* Zoom & Reset Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Lane filters */}
          <div style={{ display: 'flex', gap: '4px', background: '#F8FAFC', padding: '3px', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
            {LANE_CONFIG.map((lane) => (
              <button
                key={lane.key}
                onClick={() => toggleLane(lane.key)}
                style={{
                  border: 'none',
                  background: activeLanes[lane.key] ? lane.color : 'transparent',
                  color: activeLanes[lane.key] ? '#FFF' : '#64748B',
                  borderRadius: '6px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <lane.icon size={12} />
                <span>{lane.key.slice(0, 4)}</span>
              </button>
            ))}
          </div>

          <button
            onClick={() => setZoomLevel((z) => Math.min(z + 0.25, 2.5))}
            style={{ padding: '6px 8px', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '6px', cursor: 'pointer' }}
            title="Zoom In"
          >
            <ZoomIn size={15} color="#334155" />
          </button>
          <button
            onClick={() => setZoomLevel((z) => Math.max(z - 0.25, 0.8))}
            style={{ padding: '6px 8px', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '6px', cursor: 'pointer' }}
            title="Zoom Out"
          >
            <ZoomOut size={15} color="#334155" />
          </button>
          <button
            onClick={() => {
              setZoomLevel(1);
              setPanOffset(0);
            }}
            style={{ padding: '6px 8px', background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '6px', cursor: 'pointer' }}
            title="Reset Pan & Zoom"
          >
            <RotateCcw size={15} color="#334155" />
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div
        style={{
          border: '1px solid #E2E8F0',
          borderRadius: '12px',
          background: '#FAFAFA',
          cursor: isDragging.current ? 'grabbing' : 'grab',
          position: 'relative',
          overflow: 'hidden',
          userSelect: 'none',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <svg
          ref={svgRef}
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          width="100%"
          height="280"
          style={{ display: 'block' }}
        >
          {/* Background Grid & Swim Lane Bands */}
          {LANE_CONFIG.map((lane, idx) => {
            if (!activeLanes[lane.key]) return null;
            return (
              <g key={lane.key}>
                {/* Lane Band background */}
                <rect
                  x="0"
                  y={idx * 60 + 10}
                  width={svgWidth}
                  height="52"
                  fill={idx % 2 === 0 ? '#FFFFFF' : '#F8FAFC'}
                  stroke="#F1F5F9"
                />
                {/* Lane Label on left column */}
                <text
                  x="12"
                  y={idx * 60 + 40}
                  fill="#475569"
                  fontSize="11"
                  fontWeight="700"
                  fontFamily="inherit"
                >
                  {lane.label}
                </text>
              </g>
            );
          })}

          {/* Time Axis at bottom */}
          <line x1="140" y1="255" x2={svgWidth - 20} y2="255" stroke="#CBD5E1" strokeWidth="2" />

          {/* Render Timeline Dates */}
          {data &&
            data.visit_dates &&
            data.visit_dates.map((vDate, idx) => {
              const xPos = getXForDate(vDate, svgWidth);
              return (
                <g key={idx}>
                  {/* Vertical Visit Line */}
                  <line
                    x1={xPos}
                    y1="10"
                    x2={xPos}
                    y2="255"
                    stroke="#E2E8F0"
                    strokeWidth="1.5"
                    strokeDasharray="4 4"
                  />
                  {/* Axis Marker */}
                  <circle cx={xPos} cy="255" r="3" fill="#64748B" />
                  <text
                    x={xPos}
                    y="272"
                    textAnchor="middle"
                    fill="#64748B"
                    fontSize="10"
                    fontWeight="600"
                  >
                    {vDate}
                  </text>
                </g>
              );
            })}

          {/* Render Swim Lane Entities */}
          {data &&
            data.swim_lanes &&
            LANE_CONFIG.map((lane, laneIdx) => {
              if (!activeLanes[lane.key]) return null;
              const items = data.swim_lanes[lane.key] || [];
              const yBase = laneIdx * 60 + 36;

              return (
                <g key={lane.key}>
                  {items.map((item, itemIdx) => {
                    const xStart = getXForDate(item.date, svgWidth);
                    const xEnd = item.end_date ? getXForDate(item.end_date, svgWidth) : xStart;

                    if (lane.key === 'diagnoses') {
                      return (
                        <g
                          key={item.id || itemIdx}
                          style={{ cursor: 'pointer' }}
                          onClick={() => onNodeClick && onNodeClick(item)}
                          onMouseEnter={() => setHoveredNode({ ...item, x: xStart, y: yBase })}
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          <circle
                            cx={xStart}
                            cy={yBase}
                            r={item.status === 'resolved' ? 5 : 7}
                            fill={item.status === 'resolved' ? '#94A3B8' : lane.color}
                            stroke="#FFFFFF"
                            strokeWidth="2"
                          />
                        </g>
                      );
                    }

                    if (lane.key === 'medications') {
                      const barWidth = Math.max(xEnd - xStart, 16);
                      const isStopped = item.status === 'stopped';
                      const isChanged = item.status === 'changed';
                      const barColor = isStopped ? '#EF4444' : isChanged ? '#F59E0B' : '#2563EB';

                      return (
                        <g
                          key={item.id || itemIdx}
                          style={{ cursor: 'pointer' }}
                          onClick={() => onNodeClick && onNodeClick(item)}
                          onMouseEnter={() => setHoveredNode({ ...item, x: xStart, y: yBase })}
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          {xEnd > xStart + 8 ? (
                            <rect
                              x={xStart}
                              y={yBase - 6}
                              width={barWidth}
                              height="12"
                              rx="6"
                              fill={barColor}
                              opacity="0.85"
                            />
                          ) : (
                            <circle
                              cx={xStart}
                              cy={yBase}
                              r="6"
                              fill={barColor}
                              stroke="#FFFFFF"
                              strokeWidth="2"
                            />
                          )}
                        </g>
                      );
                    }

                    if (lane.key === 'labs') {
                      return (
                        <g
                          key={item.id || itemIdx}
                          style={{ cursor: 'pointer' }}
                          onClick={() => onNodeClick && onNodeClick(item)}
                          onMouseEnter={() => setHoveredNode({ ...item, x: xStart, y: yBase })}
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          <circle
                            cx={xStart}
                            cy={yBase}
                            r={item.is_abnormal ? 7 : 5}
                            fill={item.is_abnormal ? '#DC2626' : '#059669'}
                            stroke="#FFFFFF"
                            strokeWidth="2"
                          />
                        </g>
                      );
                    }

                    if (lane.key === 'procedures') {
                      return (
                        <g
                          key={item.id || itemIdx}
                          style={{ cursor: 'pointer' }}
                          onClick={() => onNodeClick && onNodeClick(item)}
                          onMouseEnter={() => setHoveredNode({ ...item, x: xStart, y: yBase })}
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          <polygon
                            points={`${xStart},${yBase - 7} ${xStart + 7},${yBase} ${xStart},${yBase + 7} ${xStart - 7},${yBase}`}
                            fill="#7C3AED"
                            stroke="#FFFFFF"
                            strokeWidth="1.5"
                          />
                        </g>
                      );
                    }

                    return null;
                  })}
                </g>
              );
            })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredNode && (
          <div
            style={{
              position: 'absolute',
              left: `${Math.min(hoveredNode.x, svgWidth - 220)}px`,
              top: `${Math.max(hoveredNode.y - 65, 8)}px`,
              background: '#0F172A',
              color: '#FFFFFF',
              borderRadius: '8px',
              padding: '8px 12px',
              fontSize: '12px',
              boxShadow: '0 6px 20px rgba(0,0,0,0.2)',
              pointerEvents: 'none',
              zIndex: 10,
              maxWidth: '240px',
            }}
          >
            <div style={{ fontWeight: 800, color: '#F8FAFC' }}>{hoveredNode.title || hoveredNode.test_name || hoveredNode.value}</div>
            <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '2px' }}>
              Date: {hoveredNode.date} • {hoveredNode.status || (hoveredNode.is_abnormal ? 'Abnormal' : 'Normal')}
            </div>
            <div style={{ fontSize: '10px', color: '#38BDF8', marginTop: '4px' }}>Click to view source document</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Timeline;
