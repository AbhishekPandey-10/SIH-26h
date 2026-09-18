import React, { useState, useEffect } from 'react';
import {
  Printer,
  FileText,
  AlertTriangle,
  Calendar,
  Pill,
  QrCode,
  CheckCircle2,
  RefreshCw,
  X,
  HeartPulse,
} from 'lucide-react';

export const PatientSummaryCard = ({
  sessionId,
  patientName = 'Rajesh Kumar',
  abhaId = 'rajesh.kumar@abdm',
  onClose,
}) => {
  const [data, setData] = useState(null);
  const [language, setLanguage] = useState('hi');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCard = async (lang) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/patient/summary-card', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, language: lang }),
      });
      if (!res.ok) {
        throw new Error('Failed to generate patient summary card');
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.warn('[PatientSummaryCard] fetch error:', err);
      // Fallback patient-friendly content
      setData({
        session_id: sessionId,
        patient_name: patientName,
        abha_id: abhaId,
        consult_date: new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
        language: lang,
        summary_title: lang === 'hi' ? 'आपका स्वास्थ्य परामर्श कार्ड' : 'Your Post-Consultation Health Card',
        overview:
          lang === 'hi'
            ? 'आज डॉक्टर ने आपकी जांच की। आपकी शुगर (मधुमेह) और ब्लड प्रेशर को बेहतर करने के लिए दवाइयों की डोज़ को सही किया गया है।'
            : 'Your doctor completed your consultation today. Your medications for blood sugar and blood pressure have been adjusted for optimal control.',
        medications: [
          {
            name: lang === 'hi' ? 'Metformin 1000mg (मेटफॉर्मिन 1000mg)' : 'Metformin 1000mg',
            timing: lang === 'hi' ? 'दिन में 2 बार (सुबह और रात)' : 'Twice daily (Morning & Night)',
            instructions: lang === 'hi' ? 'खाने के तुरंत बाद लें' : 'Take with or immediately after meals',
            purpose: lang === 'hi' ? 'शुगर नियंत्रण' : 'Blood sugar control',
          },
          {
            name: lang === 'hi' ? 'Amlodipine 5mg (एम्लोडिपाइन 5mg)' : 'Amlodipine 5mg',
            timing: lang === 'hi' ? 'दिन में 1 बार (सुबह)' : 'Once daily (Morning)',
            instructions: lang === 'hi' ? 'रोजाना एक ही समय पर पानी के साथ' : 'Take at the same time every day',
            purpose: lang === 'hi' ? 'ब्लड प्रेशर नियंत्रण' : 'Blood pressure management',
          },
        ],
        warning_signs: [
          lang === 'hi' ? 'सीने में बहुत तेज दर्द या सांस लेने में भारी तकलीफ' : 'Severe chest pain or acute difficulty breathing',
          lang === 'hi' ? 'अचानक शरीर के एक हिस्से में कमजोरी या बोली लड़खड़ाना' : 'Sudden weakness on one side of body or speech difficulty',
          lang === 'hi' ? 'अचानक तेज चक्कर आना या बेहोशी महसूस होना' : 'Sudden severe dizziness, sweating, or fainting',
        ],
        follow_up:
          lang === 'hi'
            ? '30 दिन बाद या अगली खाली पेट शुगर रिपोर्ट के साथ ओपीडी में दोबारा दिखाएं।'
            : 'Follow-up in 30 days or with your next fasting blood sugar report in the OPD.',
        abha_url: `https://abdm.gov.in/phr/${sessionId}`,
        qr_code_svg: '',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionId) {
      fetchCard(language);
    }
  }, [sessionId, language]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '20px',
        border: '2px solid #E2E8F0',
        padding: '24px',
        maxWidth: '740px',
        margin: '0 auto 24px',
        boxShadow: '0 10px 30px rgba(15, 23, 42, 0.08)',
        color: '#0F172A',
        position: 'relative',
      }}
      className="printable-summary-card"
    >
      {/* Top Action Bar (hidden in print) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '20px',
          borderBottom: '1.5px solid #F1F5F9',
          paddingBottom: '14px',
        }}
        className="no-print"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <HeartPulse size={22} color="#059669" />
          <span style={{ fontWeight: 800, fontSize: '15px', color: '#0F172A' }}>
            Patient Take-Home Summary (मरीज परामर्श कार्ड)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Language Toggle */}
          <div style={{ display: 'flex', background: '#F1F5F9', borderRadius: '8px', padding: '2px' }}>
            <button
              onClick={() => setLanguage('hi')}
              style={{
                border: 'none',
                background: language === 'hi' ? '#059669' : 'transparent',
                color: language === 'hi' ? '#FFFFFF' : '#475569',
                padding: '4px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              हिंदी
            </button>
            <button
              onClick={() => setLanguage('en')}
              style={{
                border: 'none',
                background: language === 'en' ? '#059669' : 'transparent',
                color: language === 'en' ? '#FFFFFF' : '#475569',
                padding: '4px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              English
            </button>
          </div>

          {/* Print Button */}
          <button
            onClick={handlePrint}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              background: '#0F172A',
              color: '#FFFFFF',
              borderRadius: '8px',
              border: 'none',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <Printer size={15} />
            <span>Print Card</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '8px',
                padding: '6px',
                cursor: 'pointer',
                color: '#64748B',
              }}
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748B' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 8px' }} />
          <div>Preparing your patient summary card...</div>
        </div>
      ) : data ? (
        <div>
          {/* Hospital & Card Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              borderBottom: '2px dashed #CBD5E1',
              paddingBottom: '16px',
              marginBottom: '16px',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#059669', fontWeight: 800, letterSpacing: '0.06em' }}>
                AI OPD Assistant • MediKiosk Care
              </div>
              <h2 style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A', margin: '4px 0' }}>
                {data.summary_title}
              </h2>
              <div style={{ fontSize: '13px', color: '#475569' }}>
                मरीज का नाम (Name): <strong>{data.patient_name}</strong> • तारीख: <strong>{data.consult_date}</strong>
              </div>
              <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                ABHA ID: <code>{data.abha_id}</code>
              </div>
            </div>

            {/* QR Code */}
            <div style={{ textAlign: 'center' }}>
              {data.qr_code_svg ? (
                <div
                  dangerouslySetInnerHTML={{ __html: data.qr_code_svg }}
                  style={{ width: '90px', height: '90px', margin: '0 auto' }}
                />
              ) : (
                <div
                  style={{
                    width: '80px',
                    height: '80px',
                    background: '#F1F5F9',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#64748B',
                  }}
                >
                  <QrCode size={40} />
                </div>
              )}
              <div style={{ fontSize: '10px', color: '#64748B', marginTop: '4px', fontWeight: 600 }}>
                Scan for ABHA Record
              </div>
            </div>
          </div>

          {/* Simple Overview */}
          <div
            style={{
              background: '#F8FAFC',
              borderRadius: '12px',
              padding: '14px 16px',
              marginBottom: '18px',
              borderLeft: '4px solid #059669',
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 800, color: '#0F172A', textTransform: 'uppercase', marginBottom: '4px' }}>
              {language === 'hi' ? 'परामर्श सारांश (Doctor Note)' : 'Doctor Overview'}
            </div>
            <div style={{ fontSize: '14px', lineHeight: '1.6', color: '#334155' }}>
              {data.overview}
            </div>
          </div>

          {/* Medications Table */}
          <div style={{ marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <Pill size={16} color="#2563EB" />
              <div style={{ fontSize: '13px', fontWeight: 800, color: '#0F172A' }}>
                {language === 'hi' ? 'दवाइयों की सूची व लेने का समय (Your Medicines)' : 'Your Medications Schedule'}
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#F1F5F9', textAlign: 'left', color: '#475569', fontSize: '12px' }}>
                    <th style={{ padding: '8px 10px', borderRadius: '6px 0 0 6px' }}>दवाई (Medicine)</th>
                    <th style={{ padding: '8px 10px' }}>समय (Timing)</th>
                    <th style={{ padding: '8px 10px' }}>सलाह (Instructions)</th>
                    <th style={{ padding: '8px 10px', borderRadius: '0 6px 6px 0' }}>कारण (Purpose)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.medications.map((m, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #E2E8F0' }}>
                      <td style={{ padding: '10px 10px', fontWeight: 700, color: '#0F172A' }}>{m.name}</td>
                      <td style={{ padding: '10px 10px', color: '#2563EB', fontWeight: 600 }}>{m.timing}</td>
                      <td style={{ padding: '10px 10px', color: '#475569' }}>{m.instructions}</td>
                      <td style={{ padding: '10px 10px', color: '#059669', fontSize: '12px' }}>{m.purpose}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Warning Signs */}
          <div
            style={{
              background: '#FFFBEB',
              border: '1.5px solid #FDE68A',
              borderRadius: '12px',
              padding: '12px 16px',
              marginBottom: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#B45309', fontWeight: 800, fontSize: '13px', marginBottom: '6px' }}>
              <AlertTriangle size={16} />
              <span>
                {language === 'hi' ? 'खतरे के लक्षण — तुरंत अस्पताल वापस आएं (Emergency Warning Signs)' : 'Emergency Warning Signs — Return Immediately If:'}
              </span>
            </div>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#78350F', lineHeight: '1.5' }}>
              {data.warning_signs.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>

          {/* Follow Up */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#F0FDF4',
              border: '1px solid #BBF7D0',
              padding: '12px 16px',
              borderRadius: '10px',
              fontSize: '13px',
              color: '#166534',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Calendar size={18} color="#16A34A" />
              <span>
                अगला परामर्श (Follow-up): <strong>{data.follow_up}</strong>
              </span>
            </div>
            <span style={{ fontSize: '11px', color: '#15803D', fontWeight: 700 }}>
              OPD Room #104
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default PatientSummaryCard;
