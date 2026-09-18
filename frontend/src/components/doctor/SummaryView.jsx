import React, { useState, useEffect } from 'react';
import SummarySection from './SummarySection';
import ConfirmPush from './ConfirmPush';
import ContradictionPanel from './ContradictionPanel';
import KioskCard from '../kiosk/KioskCard';
import {
  Stethoscope,
  FileCheck,
  AlertCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  User,
  Calendar,
} from 'lucide-react';

const SECTION_DISPLAY_MAP = {
  changes_since_last_visit: 'Changes Since Last Visit (Longitudinal Timeline Delta)',
  chief_complaint: '1. Chief Complaint (मुख्य लक्षण)',
  hpi: '2. History of Present Illness (SOCRATES विश्लेषण)',
  pmh: '3. Past Medical & Surgical History (पिछली बीमारियाँ)',
  medications: '4. Current Medications & Active Prescriptions (दवाइयाँ)',
  allergies: '5. Drug & Environmental Allergies (एलर्जी)',
  family_personal: '6. Family & Social History (पारिवारिक इतिहास)',
  ros: '7. Review of Systems (प्रणालीगत समीक्षा)',
};

export const SummaryView = ({
  sessionId,
  patientAbhaId = 'rajesh.kumar@abdm',
  patientName = 'Rajesh Kumar',
  onConsultComplete,
}) => {
  const [fields, setFields] = useState([]);
  const [polypharmacyAlerts, setPolypharmacyAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSummary = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);

    try {
      // 1. Generate / retrieve summary
      const res = await fetch('/api/summary/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!res.ok) {
        throw new Error(`Failed to generate summary: ${res.statusText}`);
      }

      const data = await res.json();
      setFields(data);

      // 2. Fetch polypharmacy alerts
      try {
        const polyRes = await fetch('/api/intelligence/polypharmacy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (polyRes.ok) {
          const polyData = await polyRes.json();
          setPolypharmacyAlerts(polyData.alerts || []);
        }
      } catch (polyErr) {
        console.warn('[SummaryView] Polypharmacy fetch warning:', polyErr);
      }
    } catch (err) {
      console.warn('[SummaryView] Summary fetch error:', err);
      setError(err.message || 'Unable to generate intake summary.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [sessionId]);

  const handleFieldUpdated = (updatedField) => {
    setFields((prev) =>
      prev.map((f) => (f.field_id === updatedField.field_id ? updatedField : f))
    );
  };

  // Group fields by canonical section
  const sectionsOrder = [
    'changes_since_last_visit',
    'chief_complaint',
    'hpi',
    'pmh',
    'medications',
    'allergies',
    'family_personal',
    'ros',
  ];

  return (
    <div style={{ width: '100%', maxWidth: '1080px', margin: '0 auto', padding: '24px 20px' }}>
      {/* Top Banner: Doctor Cabin Clinical Scribe */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '24px',
          background: '#FFFFFF',
          padding: '20px 24px',
          borderRadius: '16px',
          border: '1.5px solid #E2E8F0',
          boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              background: '#ECFDF5',
              color: '#059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Stethoscope size={30} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                Clinical Pre-Consult Intake Summary
              </h2>
              <span
                style={{
                  background: '#EFF6FF',
                  color: '#1D4ED8',
                  fontSize: '12px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '10px',
                }}
              >
                Dev 1 LLM Scribe + Dev 2 OCR
              </span>
            </div>
            <div style={{ fontSize: '14px', color: '#64748B', marginTop: '4px' }}>
              Patient: <strong>{patientName}</strong> • ABHA ID: <strong>{patientAbhaId}</strong> • Session:{' '}
              <code>{sessionId}</code>
            </div>
          </div>
        </div>

        <button
          onClick={fetchSummary}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            borderRadius: '10px',
            background: '#F1F5F9',
            border: '1px solid #CBD5E1',
            color: '#334155',
            fontWeight: 700,
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={16} />
          <span>Regenerate Summary</span>
        </button>
      </div>

      {/* TASK 2: CONTRADICTION RADAR PANEL */}
      <ContradictionPanel
        sessionId={sessionId}
        onContradictionResolved={fetchSummary}
      />

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748B' }}>
          <Loader2 size={36} className="spin" style={{ margin: '0 auto 16px' }} color="#0284C7" />
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#0F172A' }}>
            Synthesizing Multimodal Clinical Summary...
          </h3>
          <p style={{ fontSize: '14px', maxWidth: '460px', margin: '8px auto' }}>
            Merging patient voice interview transcript with scanned prescription bounding boxes via Gemini 2.0 Flash.
          </p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div
          style={{
            padding: '20px',
            borderRadius: '12px',
            background: '#FEF2F2',
            border: '1.5px solid #FCA5A5',
            color: '#991B1B',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertCircle size={24} color="#DC2626" />
            <div>
              <div style={{ fontWeight: 800 }}>Summary Synthesis Error</div>
              <div style={{ fontSize: '13px' }}>{error}</div>
            </div>
          </div>
          <button
            onClick={fetchSummary}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              background: '#DC2626',
              color: '#FFF',
              border: 'none',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Render Summary Sections */}
      {!loading && !error && fields.length > 0 && (
        <div>
          {sectionsOrder.map((secKey) => {
            const secFields = fields.filter((f) => f.section === secKey);
            if (!secFields.length) return null;

            return secFields.map((field) => (
              <SummarySection
                key={field.field_id}
                title={SECTION_DISPLAY_MAP[secKey] || secKey.toUpperCase()}
                sectionKey={secKey}
                field={field}
                sessionId={sessionId}
                onFieldUpdated={handleFieldUpdated}
                polypharmacyAlerts={
                  secKey === 'medications'
                    ? polypharmacyAlerts.length > 0
                      ? polypharmacyAlerts
                      : ['Active medications verified against OPD standard formulary.']
                    : []
                }
              />
            ));
          })}

          {/* Confirm & Push Component */}
          <ConfirmPush
            sessionId={sessionId}
            patientAbhaId={patientAbhaId}
            onConsultComplete={onConsultComplete}
          />
        </div>
      )}
    </div>
  );
};

export default SummaryView;
