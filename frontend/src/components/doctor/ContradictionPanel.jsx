import React, { useState, useEffect } from 'react';
import ClickToSource from './ClickToSource';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  HelpCircle,
  Tag,
} from 'lucide-react';

const CHANGE_TYPE_CONFIG = {
  dosage_change: {
    label: 'Dosage Changed',
    color: '#D97706',
    bg: '#FEF3C7',
    border: '#FCD34D',
    icon: '↑',
  },
  started: {
    label: 'New Medication Started',
    color: '#15803D',
    bg: '#DCFCE7',
    border: '#86EFAC',
    icon: '+',
  },
  stopped: {
    label: 'Medication Discontinued',
    color: '#DC2626',
    bg: '#FEE2E2',
    border: '#FCA5A5',
    icon: '↓',
  },
  new_diagnosis: {
    label: 'New Diagnosis',
    color: '#7C3AED',
    bg: '#EDE9FE',
    border: '#C4B5FD',
    icon: '★',
  },
  discrepancy: {
    label: 'Data Discrepancy',
    color: '#C2410C',
    bg: '#FFEDD5',
    border: '#FDBA74',
    icon: '≠',
  },
};

/**
 * <ContradictionPanel />
 * PS ID26047 — Contradiction Radar (Changes Detected Since Last Visit)
 */
export const ContradictionPanel = ({
  sessionId,
  onContradictionResolved,
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [contradictions, setContradictions] = useState([]);
  const [deltaSummary, setDeltaSummary] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState({});

  const fetchContradictions = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/intelligence/contradictions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`HTTP error: ${res.statusText}`);
      const data = await res.json();
      setContradictions(data.contradictions || []);
      setDeltaSummary(data.delta_summary || '');
    } catch (err) {
      console.warn('[ContradictionPanel] Error fetching contradictions:', err);
      // Fallback sample contradiction for offline testing
      const sample = [
        {
          id: 'contra_sample_01',
          field: 'medication',
          old_value: 'Metformin 500mg BD',
          old_source: 'Prescription dated 2025-01-10',
          new_value: 'Metformin 1000mg',
          new_source: 'Patient stated in interview',
          change_type: 'dosage_change',
          significance: 'high',
          status: 'unreviewed',
          old_source_ref: {
            type: 'document',
            ref_id: 'ent_med_01',
            document_id: 'doc_prev_presc_01',
            bounding_box: [0.12, 0.34, 0.45, 0.08],
            confidence: 0.95,
            snippet: 'Tab Glycomet 500mg BD',
          },
          new_source_ref: {
            type: 'transcript',
            ref_id: 'q_med_01',
            snippet: 'डॉक्टर साहब ने शुगर की गोली 1000mg कर दी थी',
          },
        },
        {
          id: 'contra_sample_02',
          field: 'medication',
          old_value: 'Glimepiride 1mg OD',
          old_source: 'Prescription dated 2025-01-10',
          new_value: 'Stopped (discontinued by doctor)',
          new_source: 'Patient stated in interview',
          change_type: 'stopped',
          significance: 'high',
          status: 'unreviewed',
          old_source_ref: {
            type: 'document',
            ref_id: 'ent_med_02',
            document_id: 'doc_prev_presc_01',
            bounding_box: [0.12, 0.44, 0.45, 0.08],
            confidence: 0.92,
            snippet: 'Tab Glimepiride 1mg OD',
          },
          new_source_ref: {
            type: 'transcript',
            ref_id: 'q_med_01',
            snippet: 'ग्लिमेपिराइड बंद कर दी है',
          },
        },
      ];
      setContradictions(sample);
      setDeltaSummary('^Metformin 500->1000mg, vStopped Glimepiride, +Amlodipine 5mg');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContradictions();
  }, [sessionId]);

  const handleAction = async (contradictionId, action) => {
    setActionLoading((prev) => ({ ...prev, [contradictionId]: true }));
    try {
      await fetch(`/api/intelligence/contradictions/${sessionId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contradiction_id: contradictionId,
          action, // 'confirm' or 'flag_error'
        }),
      });

      // Update state locally
      setContradictions((prev) =>
        prev.map((c) =>
          c.id === contradictionId
            ? { ...c, status: action === 'confirm' ? 'confirmed' : 'flagged_error' }
            : c
        )
      );

      if (onContradictionResolved) {
        onContradictionResolved(contradictionId, action);
      }
    } catch (err) {
      console.warn('[ContradictionPanel] Action error:', err);
    } finally {
      setActionLoading((prev) => ({ ...prev, [contradictionId]: false }));
    }
  };

  if (!loading && contradictions.length === 0) return null;

  return (
    <div
      style={{
        background: '#FFFDF5',
        borderRadius: '16px',
        border: '2px solid #F59E0B',
        boxShadow: '0 4px 16px rgba(245, 158, 11, 0.12)',
        overflow: 'hidden',
        marginBottom: '24px',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Header Bar */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          background: '#FEF3C7',
          borderBottom: isOpen ? '1.5px solid #FDE68A' : 'none',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: '#D97706',
              color: '#FFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <AlertTriangle size={20} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px', fontWeight: 800, color: '#92400E' }}>
                Changes Detected Since Last Visit (Contradiction Radar)
              </span>
              <span
                style={{
                  background: '#F59E0B',
                  color: '#FFF',
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '10px',
                }}
              >
                {contradictions.length} DETECTED
              </span>
            </div>
            {deltaSummary && (
              <div style={{ fontSize: '13px', color: '#B45309', marginTop: '2px', fontWeight: 600 }}>
                Delta: <code>{deltaSummary}</code>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetchContradictions();
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#92400E',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '4px',
            }}
            title="Refresh Contradictions"
          >
            <RefreshCw size={16} />
          </button>
          {isOpen ? <ChevronUp size={22} color="#92400E" /> : <ChevronDown size={22} color="#92400E" />}
        </div>
      </div>

      {/* Collapsible Content */}
      {isOpen && (
        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#92400E' }}>
              Comparing current interview statements with historical records...
            </div>
          ) : (
            contradictions.map((c) => {
              const typeCfg = CHANGE_TYPE_CONFIG[c.change_type] || CHANGE_TYPE_CONFIG.discrepancy;
              const isResolved = c.status === 'confirmed' || c.status === 'flagged_error';

              return (
                <div
                  key={c.id}
                  style={{
                    background: '#FFFFFF',
                    borderRadius: '12px',
                    border: isResolved ? '1.5px solid #E2E8F0' : '1.5px solid #FCD34D',
                    padding: '16px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
                    opacity: isResolved ? 0.85 : 1,
                    transition: 'all 0.15s ease',
                  }}
                >
                  {/* Top Card Row: Change Type & Significance */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 9px',
                          borderRadius: '6px',
                          background: typeCfg.bg,
                          border: `1px solid ${typeCfg.border}`,
                          color: typeCfg.color,
                          fontSize: '12px',
                          fontWeight: 800,
                        }}
                      >
                        <span>{typeCfg.icon}</span>
                        <span>{typeCfg.label}</span>
                      </span>

                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: 700,
                          background:
                            c.significance === 'high'
                              ? '#FEE2E2'
                              : c.significance === 'medium'
                              ? '#FEF3C7'
                              : '#F1F5F9',
                          color:
                            c.significance === 'high'
                              ? '#DC2626'
                              : c.significance === 'medium'
                              ? '#D97706'
                              : '#64748B',
                        }}
                      >
                        {c.significance.toUpperCase()} PRIORITY
                      </span>
                    </div>

                    {/* Status Badge if Acted On */}
                    {isResolved && (
                      <span
                        style={{
                          fontSize: '12px',
                          fontWeight: 800,
                          color: c.status === 'confirmed' ? '#15803D' : '#DC2626',
                          background: c.status === 'confirmed' ? '#DCFCE7' : '#FEE2E2',
                          padding: '3px 10px',
                          borderRadius: '12px',
                        }}
                      >
                        {c.status === 'confirmed' ? '✓ Change Acknowledged' : '⚠ Flagged as Error'}
                      </span>
                    )}
                  </div>

                  {/* Comparison Grid: Old Record vs Today's Statement */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr auto 1fr',
                      gap: '12px',
                      alignItems: 'center',
                      background: '#F8FAFC',
                      padding: '14px',
                      borderRadius: '10px',
                      border: '1px solid #E2E8F0',
                    }}
                  >
                    {/* Left: Previous Visit */}
                    <div>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>
                        Previous Record:
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A', marginTop: '2px' }}>
                        {c.old_value}
                      </div>
                      <div style={{ marginTop: '6px' }}>
                        {c.old_source_ref ? (
                          <ClickToSource
                            singleSource={c.old_source_ref}
                            customLabel={`Source: ${c.old_source}`}
                            inline
                          />
                        ) : (
                          <span style={{ fontSize: '12px', color: '#64748B' }}>{c.old_source}</span>
                        )}
                      </div>
                    </div>

                    {/* Center Arrow */}
                    <div style={{ color: '#94A3B8' }}>
                      <ArrowRight size={20} />
                    </div>

                    {/* Right: Today's Consultation */}
                    <div>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: '#2563EB', textTransform: 'uppercase' }}>
                        Today's Intake:
                      </div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#1E40AF', marginTop: '2px' }}>
                        {c.new_value}
                      </div>
                      <div style={{ marginTop: '6px' }}>
                        {c.new_source_ref ? (
                          <ClickToSource
                            singleSource={c.new_source_ref}
                            customLabel={`Source: ${c.new_source}`}
                            inline
                          />
                        ) : (
                          <span style={{ fontSize: '12px', color: '#2563EB' }}>{c.new_source}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Doctor Action Buttons */}
                  {!isResolved && (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'flex-end',
                        gap: '10px',
                        marginTop: '12px',
                        paddingTop: '10px',
                        borderTop: '1px solid #F1F5F9',
                      }}
                    >
                      <button
                        onClick={() => handleAction(c.id, 'flag_error')}
                        disabled={actionLoading[c.id]}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 14px',
                          borderRadius: '8px',
                          border: '1px solid #FCA5A5',
                          background: '#FEF2F2',
                          color: '#B91C1C',
                          fontWeight: 700,
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                      >
                        <AlertCircle size={14} />
                        <span>Flag as Error</span>
                      </button>

                      <button
                        onClick={() => handleAction(c.id, 'confirm')}
                        disabled={actionLoading[c.id]}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 16px',
                          borderRadius: '8px',
                          border: 'none',
                          background: '#15803D',
                          color: '#FFF',
                          fontWeight: 700,
                          fontSize: '12px',
                          cursor: 'pointer',
                          boxShadow: '0 2px 6px rgba(21,128,61,0.2)',
                        }}
                      >
                        <CheckCircle2 size={14} />
                        <span>Confirm Change</span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default ContradictionPanel;
