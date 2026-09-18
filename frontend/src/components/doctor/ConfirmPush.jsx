import React, { useState } from 'react';
import {
  CheckCircle,
  CloudUpload,
  ChevronDown,
  ChevronUp,
  FileCode,
  ShieldCheck,
  Loader2,
  AlertCircle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

export const ConfirmPush = ({
  sessionId,
  patientAbhaId = 'rajesh.kumar@abdm',
  onConsultComplete,
}) => {
  const [isAffirmed, setIsAffirmed] = useState(false);
  const [showFhirPreview, setShowFhirPreview] = useState(false);
  const [fhirData, setFhirData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [pushStatus, setPushStatus] = useState('idle'); // idle | pushing | success | error
  const [abdmRefId, setAbdmRefId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Load FHIR JSON preview on toggle
  const handleTogglePreview = async () => {
    if (!showFhirPreview && !fhirData) {
      setLoadingPreview(true);
      try {
        const res = await fetch(`/api/fhir/preview/${sessionId}?patient_abha_id=${patientAbhaId}`);
        if (res.ok) {
          const data = await res.json();
          setFhirData(data);
        }
      } catch (err) {
        console.warn('[ConfirmPush] Error loading FHIR preview:', err);
      } finally {
        setLoadingPreview(false);
      }
    }
    setShowFhirPreview(!showFhirPreview);
  };

  // Push to ABDM
  const handlePushToABDM = async () => {
    if (!isAffirmed) return;
    setPushStatus('pushing');
    setErrorMessage(null);

    try {
      const res = await fetch('/api/fhir/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          patient_abha_id: patientAbhaId,
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setPushStatus('success');
        setAbdmRefId(data.abdm_ref || `ABDM-TXN-${Date.now().toString().slice(-6)}`);
        if (onConsultComplete) {
          setTimeout(() => onConsultComplete(), 2000);
        }
      } else {
        throw new Error(data.message || data.error || 'ABDM Sandbox gateway connection failed.');
      }
    } catch (err) {
      console.error('[ConfirmPush] Push error:', err);
      setPushStatus('error');
      setErrorMessage(err.message || 'Push to ABDM failed. Please retry.');
    }
  };

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '16px',
        border: '2px solid #E2E8F0',
        padding: '24px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
        marginTop: '24px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <div
          style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: '#EFF6FF',
            color: '#2563EB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <CloudUpload size={24} />
        </div>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
            Physician Clinical Affirmation & ABDM Push
          </h3>
          <span style={{ fontSize: '13px', color: '#64748B' }}>
            Ayushman Bharat Digital Mission (M2/M3 Milestone Integration)
          </span>
        </div>
      </div>

      {/* RMP Affirmation Checkbox */}
      <div
        style={{
          padding: '16px',
          borderRadius: '12px',
          background: isAffirmed ? '#F0FDF4' : '#F8FAFC',
          border: `1.5px solid ${isAffirmed ? '#86EFAC' : '#E2E8F0'}`,
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          cursor: 'pointer',
        }}
        onClick={() => setIsAffirmed(!isAffirmed)}
      >
        <input
          type="checkbox"
          checked={isAffirmed}
          onChange={(e) => setIsAffirmed(e.target.checked)}
          style={{ width: '20px', height: '20px', cursor: 'pointer', marginTop: '2px' }}
        />
        <div>
          <div style={{ fontSize: '14px', fontWeight: 800, color: '#0F172A' }}>
            I affirm that I have clinically reviewed, verified, and confirmed this intake summary.
          </div>
          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px', lineHeight: 1.4 }}>
            As the Registered Medical Practitioner (RMP), I maintain sole clinical authority under CDSS guidelines.
            I authorize converting this verified record into a signed FHIR R4 Bundle linked to ABHA ID <strong>{patientAbhaId}</strong>.
          </div>
        </div>
      </div>

      {/* Expandable FHIR Preview Bar */}
      <div style={{ marginBottom: '16px' }}>
        <button
          onClick={handleTogglePreview}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: '#F1F5F9',
            border: '1px solid #CBD5E1',
            borderRadius: '8px',
            padding: '8px 14px',
            fontSize: '13px',
            fontWeight: 700,
            color: '#334155',
            cursor: 'pointer',
          }}
        >
          <FileCode size={16} />
          <span>{showFhirPreview ? 'Hide FHIR R4 Bundle JSON' : 'Preview FHIR R4 Bundle JSON'}</span>
          {showFhirPreview ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showFhirPreview && (
          <div
            style={{
              marginTop: '10px',
              padding: '16px',
              borderRadius: '10px',
              background: '#0F172A',
              color: '#38BDF8',
              fontFamily: 'monospace',
              fontSize: '12px',
              maxHeight: '300px',
              overflow: 'auto',
              border: '1px solid #334155',
            }}
          >
            {loadingPreview ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94A3B8' }}>
                <Loader2 size={16} className="spin" />
                <span>Generating standard HL7 FHIR Bundle...</span>
              </div>
            ) : (
              <pre style={{ margin: 0 }}>{JSON.stringify(fhirData, null, 2)}</pre>
            )}
          </div>
        )}
      </div>

      {/* Success Toast */}
      {pushStatus === 'success' && (
        <div
          style={{
            padding: '16px',
            borderRadius: '12px',
            background: '#ECFDF5',
            border: '2px solid #10B981',
            color: '#065F46',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <CheckCircle size={28} color="#059669" />
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800 }}>
              OPD Summary Successfully Pushed to ABDM Gateway!
            </div>
            <div style={{ fontSize: '13px', color: '#047857', marginTop: '2px' }}>
              National Health Record Ref: <strong>{abdmRefId}</strong> • Status: <em>Consult Complete</em>
            </div>
          </div>
        </div>
      )}

      {/* Error Banner with Retry */}
      {pushStatus === 'error' && (
        <div
          style={{
            padding: '14px 16px',
            borderRadius: '12px',
            background: '#FEF2F2',
            border: '1.5px solid #F87171',
            color: '#991B1B',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={22} color="#DC2626" />
            <span style={{ fontSize: '13px', fontWeight: 700 }}>{errorMessage}</span>
          </div>
          <button
            onClick={handlePushToABDM}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              background: '#DC2626',
              color: '#FFF',
              border: 'none',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <RotateCcw size={14} />
            <span>Retry Push</span>
          </button>
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
        <button
          onClick={handlePushToABDM}
          disabled={!isAffirmed || pushStatus === 'pushing' || pushStatus === 'success'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 24px',
            borderRadius: '10px',
            background: isAffirmed && pushStatus !== 'success' ? '#059669' : '#94A3B8',
            color: '#FFF',
            border: 'none',
            fontSize: '15px',
            fontWeight: 800,
            cursor: isAffirmed && pushStatus !== 'success' ? 'pointer' : 'not-allowed',
            boxShadow: isAffirmed ? '0 4px 12px rgba(5, 150, 105, 0.3)' : 'none',
            transition: 'all 0.15s ease',
          }}
        >
          {pushStatus === 'pushing' ? (
            <>
              <Loader2 size={18} className="spin" />
              <span>Transmitting to ABDM Gateway...</span>
            </>
          ) : pushStatus === 'success' ? (
            <>
              <CheckCircle size={18} />
              <span>Pushed to ABDM (Complete)</span>
            </>
          ) : (
            <>
              <CloudUpload size={18} />
              <span>Confirm & Push to ABDM</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default ConfirmPush;
