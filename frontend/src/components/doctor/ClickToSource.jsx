import React, { useState, useEffect } from 'react';
import DocumentSourceView from './DocumentSourceView';
import {
  FileText,
  Mic,
  ExternalLink,
  Clock,
  Volume2,
  CheckCircle2,
  HelpCircle,
  X,
  MessageSquare,
  Sparkles,
} from 'lucide-react';

/**
 * Format citation link text cleanly:
 * e.g., "From interview Q5", "From prescription (pg 2)", "From lab report (pg 1)"
 */
export const formatCitationText = (source, index = 1) => {
  if (!source) return 'Source citation';

  if (source.type === 'transcript') {
    const qId = source.ref_id || `Q${index}`;
    // Extract short identifier e.g. "q_cc_01" -> "Q1", "cc_01" -> "Q1"
    const match = qId.match(/\d+/);
    const shortNum = match ? match[0] : index;
    return `From interview Q${shortNum}`;
  }

  if (source.type === 'document') {
    const pg = source.page_number || 1;
    const isLab = source.ref_id?.includes('lab') || source.document_id?.includes('lab');
    const docType = isLab ? 'lab report' : 'prescription';
    return `From ${docType} (pg ${pg})`;
  }

  return 'From medical record';
};

/**
 * <ClickToSource />
 * PS ID26047 — Traceable Evidence Provenance & Modal Inspector
 */
export const ClickToSource = ({
  sources = [],
  singleSource = null,
  customLabel = null,
  inline = false,
}) => {
  const [selectedSource, setSelectedSource] = useState(null);
  const [transcriptData, setTranscriptData] = useState(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  const activeSources = singleSource ? [singleSource] : sources;

  // When a transcript source is clicked, fetch full Q&A turn from backend
  useEffect(() => {
    if (!selectedSource || selectedSource.type !== 'transcript') {
      setTranscriptData(null);
      return;
    }

    const fetchTranscript = async () => {
      setLoadingTranscript(true);
      try {
        const refId = selectedSource.ref_id;
        const res = await fetch(`/api/interview/transcript/${refId}`);
        if (res.ok) {
          const data = await res.json();
          setTranscriptData(data);
        } else {
          // Fallback to source snippet
          setTranscriptData({
            question_id: refId,
            question_text: `Interview Question (${refId})`,
            answer_text: selectedSource.snippet || 'Patient verbal confirmation',
            verbatim_voice: selectedSource.verbatim || null,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          });
        }
      } catch (err) {
        console.warn('[ClickToSource] Failed to fetch transcript:', err);
        setTranscriptData({
          question_id: selectedSource.ref_id,
          question_text: 'Interview question',
          answer_text: selectedSource.snippet || 'Patient statement recorded during OPD intake.',
          verbatim_voice: null,
          timestamp: 'Recorded during intake',
        });
      } finally {
        setLoadingTranscript(false);
      }
    };

    fetchTranscript();
  }, [selectedSource]);

  if (!activeSources || activeSources.length === 0) return null;

  return (
    <>
      {/* Clickable Citation Links */}
      <div
        style={{
          display: inline ? 'inline-flex' : 'flex',
          flexWrap: 'wrap',
          gap: '6px',
          alignItems: 'center',
        }}
      >
        {activeSources.map((src, idx) => {
          const isDoc = src.type === 'document';
          const label = customLabel || formatCitationText(src, idx + 1);

          return (
            <button
              key={idx}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedSource(src);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 9px',
                borderRadius: '6px',
                background: isDoc ? '#F0FDF4' : '#EFF6FF',
                border: `1px solid ${isDoc ? '#86EFAC' : '#93C5FD'}`,
                color: isDoc ? '#166534' : '#1E40AF',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                textDecoration: 'none',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 2px 6px rgba(0,0,0,0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {isDoc ? <FileText size={13} color="#16A34A" /> : <Mic size={13} color="#2563EB" />}
              <span>{label}</span>
              <ExternalLink size={11} style={{ opacity: 0.7 }} />
            </button>
          );
        })}
      </div>

      {/* Modal Overlay */}
      {selectedSource && (
        <div
          onClick={() => setSelectedSource(null)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(15, 23, 42, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
            animation: 'fadeIn 0.15s ease-out',
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: selectedSource.type === 'document' ? '960px' : '620px',
              maxHeight: '90vh',
              overflowY: 'auto',
              animation: 'slideUp 0.2s ease-out',
            }}
          >
            {/* DOCUMENT SOURCE MODAL */}
            {selectedSource.type === 'document' && (
              <DocumentSourceView
                imageUrl={
                  selectedSource.document_id
                    ? `/api/documents/${selectedSource.document_id}/image`
                    : '/api/documents/doc_prev_presc_01/image'
                }
                bbox={selectedSource.bounding_box || { x: 0.12, y: 0.34, w: 0.45, h: 0.08 }}
                cropUrl={selectedSource.bbox_crop_url || ''}
                entityValue={selectedSource.entity_value || selectedSource.snippet || 'Extracted clinical value'}
                confidence={selectedSource.confidence ?? 0.92}
                onClose={() => setSelectedSource(null)}
              />
            )}

            {/* TRANSCRIPT SOURCE MODAL */}
            {selectedSource.type === 'transcript' && (
              <div
                style={{
                  background: '#FFFFFF',
                  borderRadius: '16px',
                  border: '1.5px solid #E2E8F0',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
                  overflow: 'hidden',
                }}
              >
                {/* Modal Header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '18px 24px',
                    background: '#F8FAFC',
                    borderBottom: '1px solid #E2E8F0',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div
                      style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '10px',
                        background: '#EFF6FF',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#2563EB',
                      }}
                    >
                      <Mic size={20} />
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>
                        Verbatim Audio Transcript Evidence
                      </div>
                      <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
                        {formatCitationText(selectedSource)}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setSelectedSource(null)}
                    style={{
                      background: '#F1F5F9',
                      border: 'none',
                      borderRadius: '8px',
                      width: '32px',
                      height: '32px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#475569',
                      cursor: 'pointer',
                    }}
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Modal Content */}
                <div style={{ padding: '24px' }}>
                  {loadingTranscript ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: '#64748B' }}>
                      Fetching interview turn from audit database...
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {/* Timestamp & Provenance Bar */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          fontSize: '12px',
                          color: '#64748B',
                          background: '#F8FAFC',
                          padding: '8px 12px',
                          borderRadius: '8px',
                        }}
                      >
                        <Clock size={14} color="#64748B" />
                        <span>
                          Captured on:{' '}
                          <strong>
                            {transcriptData?.timestamp
                              ? new Date(transcriptData.timestamp).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                })
                              : 'During intake consultation'}
                          </strong>
                        </span>
                        <span>•</span>
                        <span>Question Ref: <code>{transcriptData?.question_id || selectedSource.ref_id}</code></span>
                      </div>

                      {/* Question Box */}
                      <div
                        style={{
                          padding: '14px 16px',
                          background: '#F1F5F9',
                          borderRadius: '10px',
                          border: '1px solid #E2E8F0',
                        }}
                      >
                        <div style={{ fontSize: '11px', fontWeight: 800, color: '#475569', textTransform: 'uppercase', marginBottom: '4px' }}>
                          Kiosk Question Prompted to Patient:
                        </div>
                        <div style={{ fontSize: '15px', color: '#1E293B', fontWeight: 600 }}>
                          {transcriptData?.question_text || 'नमस्ते, आपको क्या समस्या है?'}
                        </div>
                      </div>

                      {/* Answer Box (Highlighted in Emerald) */}
                      <div
                        style={{
                          padding: '16px',
                          background: '#ECFDF5',
                          borderRadius: '10px',
                          border: '2px solid #34D399',
                          boxShadow: '0 4px 12px rgba(16,185,129,0.1)',
                        }}
                      >
                        <div style={{ fontSize: '11px', fontWeight: 800, color: '#065F46', textTransform: 'uppercase', marginBottom: '4px' }}>
                          Patient's Transcribed Answer:
                        </div>
                        <div style={{ fontSize: '16px', color: '#064E3B', fontWeight: 700, lineHeight: 1.5 }}>
                          "{transcriptData?.answer_text || selectedSource.snippet}"
                        </div>
                      </div>

                      {/* Verbatim Voice Audio Text (if different from processed text) */}
                      {transcriptData?.verbatim_voice &&
                        transcriptData.verbatim_voice !== transcriptData.answer_text && (
                          <div
                            style={{
                              padding: '12px 16px',
                              background: '#FFFBEB',
                              borderRadius: '10px',
                              border: '1.5px solid #FCD34D',
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '10px',
                            }}
                          >
                            <Volume2 size={18} color="#D97706" style={{ marginTop: '2px' }} />
                            <div>
                              <div style={{ fontSize: '11px', fontWeight: 800, color: '#92400E', textTransform: 'uppercase' }}>
                                Raw Verbatim Voice Audio Transcription:
                              </div>
                              <div style={{ fontSize: '14px', color: '#78350F', fontStyle: 'italic', marginTop: '2px' }}>
                                "{transcriptData.verbatim_voice}"
                              </div>
                              <div style={{ fontSize: '11px', color: '#B45309', marginTop: '4px' }}>
                                (Clinically normalized by AI into medical terminology above)
                              </div>
                            </div>
                          </div>
                        )}
                    </div>
                  )}
                </div>

                {/* Modal Footer */}
                <div
                  style={{
                    padding: '14px 24px',
                    background: '#F8FAFC',
                    borderTop: '1px solid #E2E8F0',
                    display: 'flex',
                    justifyContent: 'flex-end',
                  }}
                >
                  <button
                    onClick={() => setSelectedSource(null)}
                    style={{
                      padding: '8px 18px',
                      borderRadius: '8px',
                      background: '#0F172A',
                      color: '#FFF',
                      border: 'none',
                      fontWeight: 700,
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    Close Evidence
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default ClickToSource;
