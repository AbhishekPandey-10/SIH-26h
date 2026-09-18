import React, { useState, useEffect } from 'react';
import {
  Bell,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Radio,
  Volume2,
} from 'lucide-react';

/**
 * <StaffAlertPanel />
 * PS ID26047 — Triage Nurse & OPD Staff Emergency Alert Monitor
 */
export const StaffAlertPanel = ({
  onAlertDismissed,
}) => {
  const [alerts, setAlerts] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [dismissReason, setDismissReason] = useState('Staff evaluated patient at kiosk; non-emergency confirmed');

  useEffect(() => {
    // Connect to /ws/staff-alerts
    let ws;
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      ws = new WebSocket(`${protocol}//${host}/ws/staff-alerts`);

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data);
          if (payload.event === 'red_flag_alert' && payload.data) {
            setAlerts((prev) => [payload.data, ...prev]);
          }
        } catch (err) {
          console.warn('[StaffAlertPanel] Parse error:', err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
      };
    } catch (err) {
      console.warn('[StaffAlertPanel] WebSocket error:', err);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleDismiss = async (eventId) => {
    try {
      const res = await fetch(`/api/red-flag/${eventId}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dismissed_by: 'nurse_station_01',
          reason: dismissReason,
        }),
      });

      if (res.ok) {
        setAlerts((prev) => prev.filter((a) => a.event_id !== eventId && a.id !== eventId));
        if (onAlertDismissed) {
          onAlertDismissed(eventId);
        }
      }
    } catch (err) {
      console.warn('[StaffAlertPanel] Dismiss error:', err);
    }
  };

  const handleAcknowledge = async (eventId) => {
    try {
      await fetch(`/api/red-flag/${eventId}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          acknowledged_by: 'nurse_station_01',
          action_taken: 'Triage nurse attending immediately',
        }),
      });
      setAlerts((prev) =>
        prev.map((a) =>
          a.event_id === eventId || a.id === eventId ? { ...a, acknowledged: true } : a
        )
      );
    } catch (err) {
      console.warn('[StaffAlertPanel] Acknowledge error:', err);
    }
  };

  if (alerts.length === 0) return null;

  return (
    <div
      style={{
        marginBottom: '20px',
        padding: '18px 22px',
        background: '#FEF2F2',
        borderRadius: '16px',
        border: '2px solid #DC2626',
        boxShadow: '0 4px 18px rgba(220, 38, 38, 0.15)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldAlert size={24} color="#DC2626" />
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: '#991B1B' }}>
              EMERGENCY RED-FLAG SAFETY ALERT (Triage Escalation)
            </div>
            <div style={{ fontSize: '12px', color: '#B91C1C' }}>
              Patient interview paused. Immediate clinical triage required.
            </div>
          </div>
        </div>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            fontWeight: 800,
            padding: '3px 8px',
            borderRadius: '10px',
            background: wsConnected ? '#DCFCE7' : '#F1F5F9',
            color: wsConnected ? '#15803D' : '#64748B',
          }}
        >
          <Radio size={12} />
          <span>{wsConnected ? 'Staff Channel Live' : 'Polling Live'}</span>
        </div>
      </div>

      {/* Alert List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {alerts.map((al, idx) => {
          const evId = al.event_id || al.id || `ev_${idx}`;
          return (
            <div
              key={evId}
              style={{
                background: '#FFFFFF',
                borderRadius: '12px',
                padding: '14px 18px',
                border: '1.5px solid #FCA5A5',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '12px',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      background: '#DC2626',
                      color: '#FFF',
                      fontSize: '11px',
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: '6px',
                    }}
                  >
                    HIGH ACUITY: {al.category?.toUpperCase() || 'CARDIAC'}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                    Trigger phrase: <em>"{al.trigger_phrase}"</em>
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px' }}>
                  Matched Rule: <code>{al.matched_rule}</code> • Session: <code>{al.session_id}</code>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleAcknowledge(evId)}
                  disabled={al.acknowledged}
                  style={{
                    padding: '7px 14px',
                    borderRadius: '8px',
                    border: '1px solid #F59E0B',
                    background: '#FEF3C7',
                    color: '#92400E',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {al.acknowledged ? '✓ Acknowledged' : 'Acknowledge Alert'}
                </button>

                <button
                  onClick={() => handleDismiss(evId)}
                  style={{
                    padding: '7px 16px',
                    borderRadius: '8px',
                    border: 'none',
                    background: '#15803D',
                    color: '#FFF',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Dismiss & Resume Kiosk
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StaffAlertPanel;
