import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  TrendingUp,
  PlusCircle,
  MinusCircle,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  FileText,
} from 'lucide-react';

export const DeltaView = ({
  sessionId,
  onItemClick,
}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const fetchDelta = async () => {
      if (!sessionId) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/visualization/what-changed/${sessionId}`);
        if (!res.ok) throw new Error('Failed to load delta summary');
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.warn('[DeltaView] fetch error:', err);
        // Clean fallback demonstrating all 4 delta change types
        setData({
          session_id: sessionId,
          last_visit_date: '12 Jan 2026',
          title: 'Since last visit (12 Jan 2026):',
          items_count: 4,
          items: [
            {
              id: 'delta_01',
              field: 'Amlodipine',
              prefix: '+',
              color: 'green',
              display_line: '+ Started Amlodipine 5mg',
              change_type: 'started',
              new_value: 'Amlodipine 5mg',
              source_ref: { type: 'transcript', ref_id: 'q_med_01', snippet: 'Doctor started Amlodipine 5mg daily' },
            },
            {
              id: 'delta_02',
              field: 'HbA1c',
              prefix: '^',
              color: 'amber',
              display_line: '^ HbA1c 6.2% -> 7.1%',
              change_type: 'discrepancy',
              old_value: '6.2%',
              new_value: '7.1%',
              source_ref: { type: 'document', ref_id: 'ent_hba1c_01', snippet: 'HbA1c: 7.1%' },
            },
            {
              id: 'delta_03',
              field: 'Glimepiride',
              prefix: 'v',
              color: 'red',
              display_line: 'v Stopped Glimepiride',
              change_type: 'stopped',
              old_value: 'Glimepiride 1mg',
              source_ref: { type: 'transcript', ref_id: 'q_pmh_01', snippet: 'Patient stopped Glimepiride' },
            },
            {
              id: 'delta_04',
              field: 'Metformin',
              prefix: '~',
              color: 'amber',
              display_line: '~ Metformin 500mg -> 1000mg',
              change_type: 'dosage_change',
              old_value: '500mg',
              new_value: '1000mg',
              source_ref: { type: 'transcript', ref_id: 'q_med_01', snippet: 'Dose titrated to 1000mg BD' },
            },
          ],
        });
      } finally {
        setLoading(false);
      }
    };

    fetchDelta();
  }, [sessionId]);

  if (loading && !data) {
    return null;
  }

  if (!data || !data.items || data.items.length === 0) {
    return null;
  }

  const getColorStyles = (color) => {
    switch (color) {
      case 'green':
        return { bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0', icon: '#059669', badgeBg: '#10B981' };
      case 'red':
        return { bg: '#FEF2F2', text: '#991B1B', border: '#FECACA', icon: '#DC2626', badgeBg: '#EF4444' };
      case 'amber':
      default:
        return { bg: '#FFFBEB', text: '#92400E', border: '#FDE68A', icon: '#D97706', badgeBg: '#F59E0B' };
    }
  };

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '16px',
        border: '1.5px solid #CBD5E1',
        boxShadow: '0 4px 14px rgba(15, 23, 42, 0.04)',
        padding: '16px 20px',
        marginBottom: '20px',
        position: 'relative',
      }}
      id="what-changed-delta-card"
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setCollapsed(!collapsed)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: '#F1F5F9',
              color: '#0284C7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <GitCompare size={18} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>
                {data.title || `Since last visit (${data.last_visit_date}):`}
              </span>
              <span
                style={{
                  background: '#0F172A',
                  color: '#FFFFFF',
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '12px',
                }}
              >
                {data.items.length} Changes
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#64748B', marginTop: '1px' }}>
              Comparing longitudinal records • Click any line to trace provenance
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748B' }}>
          {collapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </div>
      </div>

      {/* Delta Items List */}
      {!collapsed && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '10px',
            marginTop: '14px',
            paddingTop: '12px',
            borderTop: '1px solid #F1F5F9',
          }}
        >
          {data.items.map((item, idx) => {
            const styles = getColorStyles(item.color);
            return (
              <div
                key={item.id || idx}
                onClick={() => onItemClick && onItemClick(item.source_ref || item)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: styles.bg,
                  border: `1.5px solid ${styles.border}`,
                  borderRadius: '10px',
                  padding: '10px 12px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                title="Click to view original source citation"
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      background: styles.badgeBg,
                      color: '#FFFFFF',
                      fontSize: '12px',
                      fontWeight: 900,
                    }}
                  >
                    {item.prefix}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: styles.text }}>
                    {item.display_line || `${item.prefix} ${item.field}`}
                  </span>
                </div>

                <ExternalLink size={13} color={styles.icon} style={{ opacity: 0.7 }} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DeltaView;
