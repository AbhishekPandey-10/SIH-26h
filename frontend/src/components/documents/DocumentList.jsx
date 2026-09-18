import React, { useState, useEffect } from 'react';
import KioskCard from '../kiosk/KioskCard';
import KioskButton from '../kiosk/KioskButton';
import BboxOverlay from './BboxOverlay';
import {
  FileText,
  Calendar,
  Layers,
  ChevronRight,
  Maximize2,
  Activity,
  Pill,
  Clock,
  CheckCircle2,
  AlertCircle,
  Stethoscope,
} from 'lucide-react';

export const DocumentList = ({
  sessionId,
  language = 'hi',
  onScanMore,
}) => {
  const [documents, setDocuments] = useState([]);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocForOverlay, setSelectedDocForOverlay] = useState(null);
  const [sortOrder, setSortOrder] = useState('chronological');

  useEffect(() => {
    if (!sessionId) return;

    async function loadDocumentsAndEntities() {
      try {
        setLoading(true);
        // 1. Fetch document list
        const docRes = await fetch(`/api/documents/${sessionId}`);
        let docs = [];
        if (docRes.ok) {
          docs = await docRes.json();
          setDocuments(docs);
        }

        // 2. Fetch extracted entities chronologically
        const entRes = await fetch(`/api/documents/entities/${sessionId}?sort=chronological`);
        if (entRes.ok) {
          const entData = await entRes.json();
          setEntities(entData.entities || []);
        }
      } catch (err) {
        console.warn('[DocumentList] Failed to load documents:', err);
      } finally {
        setLoading(false);
      }
    }

    loadDocumentsAndEntities();
  }, [sessionId]);

  const getDocTypeBadge = (fileType) => {
    switch (fileType) {
      case 'prescription':
        return { label: 'Prescription / पर्चा', bg: '#EFF6FF', color: '#1D4ED8', border: '#BFDBFE' };
      case 'lab':
        return { label: 'Lab Report / जांच', bg: '#ECFDF5', color: '#047857', border: '#A7F3D0' };
      case 'discharge':
        return { label: 'Discharge Summary', bg: '#FAF5FF', color: '#7E22CE', border: '#E9D5FF' };
      default:
        return { label: 'Medical Record', bg: '#F1F5F9', color: '#475569', border: '#CBD5E1' };
    }
  };

  return (
    <div style={{ width: '100%', maxWidth: '960px', margin: '0 auto', padding: '24px 20px' }}>
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '24px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
            {language === 'hi' ? 'स्कैन किए गए दस्तावेज़ एवं दवाइयां' : 'Scanned Documents & Extracted Entities'}
          </h2>
          <span style={{ fontSize: '14px', color: '#64748B' }}>
            {language === 'hi'
              ? `${documents.length} दस्तावेज़ एवं ${entities.length} सत्यापित दवाइयां / जांच परिणाम`
              : `${documents.length} Scanned records · ${entities.length} extracted clinical items`}
          </span>
        </div>

        {onScanMore && (
          <KioskButton variant="primary" size="md" onClick={onScanMore}>
            {language === 'hi' ? '+ और दस्तावेज़ स्कैन करें' : '+ Scan More Documents'}
          </KioskButton>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '48px', color: '#64748B' }}>
          <span>लोड हो रहा है... (Loading medical records...)</span>
        </div>
      ) : documents.length === 0 ? (
        <KioskCard padding="40px" style={{ textAlign: 'center' }}>
          <FileText size={48} color="#94A3B8" style={{ marginBottom: '16px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#0F172A' }}>
            {language === 'hi' ? 'कोई दस्तावेज़ अभी स्कैन नहीं किया गया है' : 'No documents scanned yet'}
          </h3>
          <p style={{ fontSize: '14px', color: '#64748B', maxWidth: '420px', margin: '8px auto 20px' }}>
            {language === 'hi'
              ? 'कागजी पर्चा अथवा लैब रिपोर्ट कैमरे से स्कैन करें ताकि डॉक्टर के लिए दवाइयों की सूची स्वतः तैयार हो सके।'
              : 'Scan past prescription slips and lab tests with the kiosk camera to automatically extract medicines.'}
          </p>
          {onScanMore && (
            <KioskButton variant="primary" size="lg" onClick={onScanMore}>
              {language === 'hi' ? 'कैमरा शुरू करें →' : 'Start Camera Scanner →'}
            </KioskButton>
          )}
        </KioskCard>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {documents.map((doc, idx) => {
            const badge = getDocTypeBadge(doc.file_type);
            const docEntities = entities.filter((e) => e.document_id === doc.document_id);
            const medsCount = docEntities.filter((e) => e.entity_type === 'medication').length;
            const labsCount = docEntities.filter((e) => e.entity_type === 'lab_value').length;
            const diagCount = docEntities.filter((e) => e.entity_type === 'diagnosis').length;

            return (
              <KioskCard
                key={doc.document_id}
                padding="24px"
                style={{
                  border: '1.5px solid #E2E8F0',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                  {/* Thumbnail Preview with tap to expand */}
                  <div
                    onClick={() => setSelectedDocForOverlay(doc)}
                    style={{
                      width: '90px',
                      height: '110px',
                      borderRadius: '10px',
                      overflow: 'hidden',
                      border: '1.5px solid #CBD5E1',
                      background: '#0F172A',
                      cursor: 'pointer',
                      position: 'relative',
                      flexShrink: 0,
                    }}
                  >
                    <img
                      src={`/api/documents/${doc.document_id}/file`}
                      alt="Thumbnail"
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        background: 'rgba(0,0,0,0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        opacity: 0.85,
                      }}
                    >
                      <Maximize2 size={22} color="#FFF" />
                    </div>
                  </div>

                  {/* Document Details & Extracted Badges */}
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <span
                        style={{
                          padding: '3px 10px',
                          borderRadius: '6px',
                          background: badge.bg,
                          color: badge.color,
                          border: `1px solid ${badge.border}`,
                          fontSize: '12px',
                          fontWeight: 800,
                        }}
                      >
                        {badge.label}
                      </span>

                      <span style={{ fontSize: '13px', color: '#64748B', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={14} />
                        <span>Page {doc.page_number}</span>
                      </span>

                      <span
                        style={{
                          fontSize: '12px',
                          color: '#059669',
                          fontWeight: 700,
                          background: '#ECFDF5',
                          padding: '2px 8px',
                          borderRadius: '12px',
                        }}
                      >
                        ✓ Extracted
                      </span>
                    </div>

                    {/* Extracted Entity Counts Pills */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      {medsCount > 0 && (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            background: '#EFF6FF',
                            color: '#1D4ED8',
                            padding: '4px 10px',
                            borderRadius: '16px',
                            fontSize: '13px',
                            fontWeight: 700,
                          }}
                        >
                          <Pill size={14} />
                          <span>{medsCount} Medications</span>
                        </span>
                      )}

                      {labsCount > 0 && (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            background: '#ECFDF5',
                            color: '#047857',
                            padding: '4px 10px',
                            borderRadius: '16px',
                            fontSize: '13px',
                            fontWeight: 700,
                          }}
                        >
                          <Activity size={14} />
                          <span>{labsCount} Lab Values</span>
                        </span>
                      )}

                      {diagCount > 0 && (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            background: '#FAF5FF',
                            color: '#7E22CE',
                            padding: '4px 10px',
                            borderRadius: '16px',
                            fontSize: '13px',
                            fontWeight: 700,
                          }}
                        >
                          <Stethoscope size={14} />
                          <span>{diagCount} Diagnoses</span>
                        </span>
                      )}
                    </div>

                    {/* Preview extracted items inline */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {docEntities.slice(0, 4).map((ent) => (
                        <span
                          key={ent.id}
                          style={{
                            background: '#F1F5F9',
                            color: '#334155',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: 600,
                          }}
                        >
                          {ent.generic_name ? `${ent.generic_name} (${ent.value})` : ent.value}
                        </span>
                      ))}
                      {docEntities.length > 4 && (
                        <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600, alignSelf: 'center' }}>
                          +{docEntities.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Inspect Button */}
                  <KioskButton
                    variant="secondary"
                    size="sm"
                    icon={<Maximize2 size={16} />}
                    onClick={() => setSelectedDocForOverlay(doc)}
                  >
                    {language === 'hi' ? 'बाउंडिंग बॉक्स देखें' : 'View Bounding Boxes'}
                  </KioskButton>
                </div>
              </KioskCard>
            );
          })}
        </div>
      )}

      {/* Full-Screen Bbox Overlay Modal */}
      {selectedDocForOverlay && (
        <BboxOverlay
          imageUrl={`/api/documents/${selectedDocForOverlay.document_id}/file`}
          documentId={selectedDocForOverlay.document_id}
          entities={entities.filter((e) => e.document_id === selectedDocForOverlay.document_id)}
          onClose={() => setSelectedDocForOverlay(null)}
        />
      )}
    </div>
  );
};

export default DocumentList;
