import React, { useState } from 'react';
import SummaryView from '../components/doctor/SummaryView';
import DocumentList from '../components/documents/DocumentList';
import {
  Stethoscope,
  FileText,
  User,
  Clock,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Hospital,
  Activity,
  Layers,
} from 'lucide-react';

export const DoctorDashboard = ({
  session,
  patient,
  onBackToKiosk,
}) => {
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'documents'
  const sessionId = session?.session_id || 'dev-test-001';
  const patientAbhaId = patient?.abha_id || 'rajesh.kumar@abdm';
  const patientName = patient?.name || 'Rajesh Kumar';

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#F8FAFC',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Doctor Navigation Bar */}
      <header
        style={{
          background: '#0F172A',
          color: '#FFF',
          padding: '14px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '2.5px solid #0284C7',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={onBackToKiosk}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '8px',
              background: '#1E293B',
              border: '1px solid rgba(255,255,255,0.15)',
              color: '#F8FAFC',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '13px',
            }}
          >
            <ArrowLeft size={16} />
            <span>Switch to Kiosk Mode</span>
          </button>

          <div style={{ height: '24px', width: '1px', background: '#334155' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: '#0284C7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Stethoscope size={20} color="#FFF" />
            </div>
            <div>
              <div style={{ fontSize: '16px', fontWeight: 800 }}>MediKiosk Doctor Command Center</div>
              <div style={{ fontSize: '11px', color: '#94A3B8' }}>AIIMS OPD Room 104 • Dr. A. Sharma, MD</div>
            </div>
          </div>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', background: '#1E293B', borderRadius: '10px', padding: '4px' }}>
          <button
            onClick={() => setActiveTab('summary')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'summary' ? '#0284C7' : 'transparent',
              color: '#FFF',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <FileText size={16} />
            <span>Clinical Intake Scribe</span>
          </button>

          <button
            onClick={() => setActiveTab('documents')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'documents' ? '#0284C7' : 'transparent',
              color: '#FFF',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Layers size={16} />
            <span>Scanned Documents & OCR</span>
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main style={{ flex: 1, padding: '24px 0' }}>
        {activeTab === 'summary' ? (
          <SummaryView
            sessionId={sessionId}
            patientAbhaId={patientAbhaId}
            patientName={patientName}
            onConsultComplete={() => alert('Consultation completed and pushed to ABDM!')}
          />
        ) : (
          <DocumentList
            sessionId={sessionId}
            language="hi"
          />
        )}
      </main>
    </div>
  );
};

export default DoctorDashboard;
