import React, { useState } from 'react';
import KioskCard from './KioskCard';
import KioskButton from './KioskButton';
import { useSession } from '../../contexts/SessionContext';
import { InterviewScreen } from '../interview/InterviewScreen';

export const KioskDashboard = () => {
  const { session, patient, language, endSession } = useSession();
  const [showInterview, setShowInterview] = useState(false);

  if (showInterview) {
    return (
      <div style={{ width: '100%', maxWidth: '900px', margin: '0 auto', padding: '24px 20px' }}>
        <button
          onClick={() => setShowInterview(false)}
          style={{
            marginBottom: '16px',
            background: 'var(--color-surface-secondary)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'var(--color-text-primary)',
            padding: '10px 18px',
            borderRadius: '10px',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '14px',
          }}
        >
          ← डैशबोर्ड पर लौटें (Back to Dashboard)
        </button>
        <InterviewScreen sessionId={session?.session_id || "dev-test-001"} language={language} />
      </div>
    );
  }

  return (
    <div style={{
      width: '100%',
      maxWidth: '900px',
      margin: '0 auto',
      padding: '32px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '28px',
    }}>
      {/* Top Banner */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '20px 24px',
        background: 'var(--color-surface-secondary)',
        borderRadius: '16px',
        border: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div>
          <span style={{ fontSize: '13px', color: 'var(--color-green-safe)', fontWeight: 700, textTransform: 'uppercase' }}>
            ● सक्रिय कियोस्क सत्र (Active Intake Session)
          </span>
          <h2 style={{ fontSize: '24px', fontWeight: 800, marginTop: '2px' }}>
            स्वागत है, {patient?.name || session?.patient_name || 'मरीज'}
          </h2>
          <span style={{ fontSize: '14px', color: 'var(--color-text-secondary)', fontFamily: 'monospace' }}>
            सत्र आईडी: {session?.session_id}
          </span>
        </div>

        <KioskButton
          variant="danger"
          size="md"
          onClick={endSession}
        >
          सत्र समाप्त एवं डेटा मिटाएं (Wipe & Exit)
        </KioskButton>
      </div>

      {/* Patient Identity Card */}
      <KioskCard padding="24px">
        <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '14px', color: 'var(--color-text-primary)' }}>
          सत्यापित मरीज पहचान (Verified Patient Details)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>ABHA ID / स्थिति:</span>
            <div style={{ fontSize: '16px', fontWeight: 600, marginTop: '2px' }}>
              {patient?.abha_id || <span style={{ color: 'var(--color-amber-warning)' }}>Session created without ABHA linkage</span>}
            </div>
          </div>
          <div>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>जन्म तिथि / लिंग:</span>
            <div style={{ fontSize: '16px', fontWeight: 600, marginTop: '2px' }}>
              {patient?.dob || '1990-01-01'} · {patient?.gender === 'M' ? 'पुरुष' : patient?.gender === 'F' ? 'महिला' : 'अन्य'}
            </div>
          </div>
          <div>
            <span style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>चयनित भाषा:</span>
            <div style={{ fontSize: '16px', fontWeight: 600, marginTop: '2px' }}>
              {language.toUpperCase()} (Bhashini AI Active)
            </div>
          </div>
        </div>
      </KioskCard>

      {/* Next Clinical Actions Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        <KioskCard
          padding="28px"
          style={{
            border: '2px solid var(--color-blue-info)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            cursor: 'pointer',
          }}
          onClick={() => setShowInterview(true)}
        >
          <div>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>🎙️</div>
            <h3 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '6px' }}>
              क्लिनिकल साक्षात्कार शुरू करें (Dev 1 Track)
            </h3>
            <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)' }}>
              SOCRATES दर्द विश्लेषण, पिछली बीमारियों और दवाइयों का आवाज-आधारित साक्षात्कार।
            </p>
          </div>
          <div style={{ marginTop: '20px' }}>
            <span style={{ color: 'var(--color-blue-info)', fontWeight: 700 }}>आवाज वार्तालाप आरंभ करें →</span>
          </div>
        </KioskCard>

        <KioskCard
          padding="28px"
          style={{
            border: '2px solid var(--color-green-safe)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            cursor: 'pointer',
          }}
          onClick={() => alert(`Dev 2 Module B Document OCR Pipeline ready with 17 pre-seeded sample documents.`)}
        >
          <div>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>📄</div>
            <h3 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '6px' }}>
              पर्चे एवं लैब रिपोर्ट स्कैन करें (Dev 2 Track)
            </h3>
            <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)' }}>
              कागजी पर्चे व टेस्ट रिपोर्ट कैमरे से स्कैन करें और बाउंडिंग बॉक्स सहित दवाइयां निकालें।
            </p>
          </div>
          <div style={{ marginTop: '20px' }}>
            <span style={{ color: 'var(--color-green-safe)', fontWeight: 700 }}>दस्तावेज़ स्कैन करें →</span>
          </div>
        </KioskCard>
      </div>
    </div>
  );
};

export default KioskDashboard;
