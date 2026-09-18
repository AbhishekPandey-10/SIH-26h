import React, { useState } from 'react';
import { VerificationBadge } from './VerificationBadge';
import AskBackPanel from './AskBackPanel';
import {
  ChevronDown,
  ChevronUp,
  Edit3,
  Check,
  RotateCcw,
  MessageSquare,
  FileText,
  AlertTriangle,
  ExternalLink,
  History,
  Pill,
} from 'lucide-react';

export const SummarySection = ({
  title,
  sectionKey,
  field,
  sessionId,
  onFieldUpdated,
  polypharmacyAlerts = [],
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(field?.content || '');
  const [isSaving, setIsSaving] = useState(false);
  const [showAskBack, setShowAskBack] = useState(false);
  const [patientAnswerNotification, setPatientAnswerNotification] = useState(null);
  const [showCropPreview, setShowCropPreview] = useState(null);

  if (!field) return null;

  const handleSaveEdit = async () => {
    if (editedContent === field.content) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      const res = await fetch(`/api/summary/${sessionId}/field/${field.field_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: editedContent,
          doctor_notes: 'Edited by physician during OPD consult',
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        setIsEditing(false);
        if (onFieldUpdated) {
          onFieldUpdated(updated);
        }
      }
    } catch (err) {
      console.warn('[SummarySection] Save edit error:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRevert = () => {
    setEditedContent(field.original_content || field.content);
    setIsEditing(false);
  };

  const handleAskBackResolved = (updatedField, answer) => {
    setPatientAnswerNotification(answer);
    setShowAskBack(false);
    if (onFieldUpdated) {
      onFieldUpdated(updatedField);
    }
  };

  const isDocEdited = field.verification === 'doctor_edited';

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '14px',
        border: isDocEdited ? '2px solid #C084FC' : '1.5px solid #E2E8F0',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
        overflow: 'hidden',
        marginBottom: '16px',
        transition: 'all 0.15s ease',
      }}
    >
      {/* Section Header */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          background: isDocEdited ? '#FAF5FF' : '#F8FAFC',
          borderBottom: isOpen ? '1px solid #E2E8F0' : 'none',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
            {title}
          </span>
          <VerificationBadge
            status={field.verification}
            sourceCount={field.sources?.length || 0}
            compact
          />
          {field.changed_since_last && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 800,
                color: '#DC2626',
                background: '#FEE2E2',
                padding: '2px 8px',
                borderRadius: '10px',
              }}
            >
              DELTA DETECTED
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowAskBack(!showAskBack);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              color: '#1D4ED8',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <MessageSquare size={14} />
            <span>Ask patient about this</span>
          </button>

          {isOpen ? <ChevronUp size={20} color="#64748B" /> : <ChevronDown size={20} color="#64748B" />}
        </div>
      </div>

      {/* Collapsible Content */}
      {isOpen && (
        <div style={{ padding: '20px' }}>
          {/* Polypharmacy Warnings (for Medications section) */}
          {sectionKey === 'medications' && polypharmacyAlerts.length > 0 && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: '10px',
                background: '#FEF3C7',
                border: '1.5px solid #F59E0B',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <AlertTriangle size={22} color="#D97706" />
              <div>
                <span style={{ fontSize: '13px', fontWeight: 800, color: '#92400E' }}>
                  POLYPHARMACY / GENERIC DUPLICATION ALERT:
                </span>
                <div style={{ fontSize: '13px', color: '#B45309' }}>
                  {polypharmacyAlerts.join(' • ')}
                </div>
              </div>
            </div>
          )}

          {/* Inline Editable Text Area */}
          {isEditing ? (
            <div>
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                style={{
                  width: '100%',
                  minHeight: '100px',
                  padding: '12px',
                  borderRadius: '10px',
                  border: '2px solid #2563EB',
                  fontSize: '15px',
                  lineHeight: 1.6,
                  color: '#0F172A',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                <button
                  onClick={handleRevert}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    background: '#FFF',
                    fontSize: '13px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <RotateCcw size={14} />
                  <span>Cancel</span>
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={isSaving}
                  style={{
                    padding: '6px 16px',
                    borderRadius: '8px',
                    border: 'none',
                    background: '#2563EB',
                    color: '#FFF',
                    fontWeight: 700,
                    fontSize: '13px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <Check size={14} />
                  <span>{isSaving ? 'Saving...' : 'Save & Verify'}</span>
                </button>
              </div>
            </div>
          ) : (
            <div style={{ position: 'relative' }}>
              <div
                style={{
                  fontSize: '15px',
                  lineHeight: 1.65,
                  color: '#1E293B',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {field.content}
              </div>

              {/* Edit Trigger Button */}
              <button
                onClick={() => {
                  setEditedContent(field.content);
                  setIsEditing(true);
                }}
                style={{
                  marginTop: '12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  background: '#F1F5F9',
                  border: '1px solid #E2E8F0',
                  color: '#475569',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Edit3 size={13} />
                <span>Edit text inline</span>
              </button>
            </div>
          )}

          {/* Audit: Original vs Edited text */}
          {field.original_content && field.original_content !== field.content && (
            <div
              style={{
                marginTop: '12px',
                padding: '10px 14px',
                borderRadius: '8px',
                background: '#F8FAFC',
                border: '1px dashed #CBD5E1',
                fontSize: '13px',
                color: '#64748B',
              }}
            >
              <span style={{ fontWeight: 700 }}>AI Drafted Statement: </span>
              <span style={{ textDecoration: 'line-through' }}>{field.original_content}</span>
            </div>
          )}

          {/* Patient Just Answered Strip */}
          {patientAnswerNotification && (
            <div
              style={{
                marginTop: '12px',
                padding: '10px 14px',
                borderRadius: '8px',
                background: '#ECFDF5',
                border: '1px solid #A7F3D0',
                color: '#065F46',
                fontSize: '13px',
                fontWeight: 600,
              }}
            >
              ✓ Patient just answered: "{patientAnswerNotification}"
            </div>
          )}

          {/* Ask-Back Panel */}
          {showAskBack && (
            <AskBackPanel
              sessionId={sessionId}
              field={field}
              onQuestionResolved={handleAskBackResolved}
              onClose={() => setShowAskBack(false)}
            />
          )}

          {/* Verified Source Citations */}
          {field.sources && field.sources.length > 0 && (
            <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid #F1F5F9' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, color: '#94A3B8', textTransform: 'uppercase' }}>
                EVIDENCE PROVENANCE ({field.sources.length} sources):
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '6px' }}>
                {field.sources.map((src, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      background: src.type === 'document' ? '#F0FDF4' : '#EFF6FF',
                      border: `1px solid ${src.type === 'document' ? '#BBF7D0' : '#BFDBFE'}`,
                      fontSize: '12px',
                      color: src.type === 'document' ? '#15803D' : '#1D4ED8',
                    }}
                  >
                    <span>{src.type === 'document' ? '📄 Document Crop' : '🎙️ Patient Voice'}</span>
                    {src.snippet && (
                      <span style={{ fontWeight: 600 }}>"{src.snippet.slice(0, 30)}..."</span>
                    )}
                    {src.bbox_crop_url && (
                      <button
                        onClick={() => setShowCropPreview(src.bbox_crop_url)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#2563EB',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          padding: 0,
                        }}
                        title="Inspect Crop"
                      >
                        <ExternalLink size={12} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mini Modal for Crop preview */}
          {showCropPreview && (
            <div
              style={{
                marginTop: '12px',
                padding: '12px',
                borderRadius: '8px',
                background: '#0F172A',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#FFF', fontSize: '12px', marginBottom: '6px' }}>
                <span>Source Bounding-Box Image Crop</span>
                <button
                  onClick={() => setShowCropPreview(null)}
                  style={{ background: 'none', border: 'none', color: '#FFF', cursor: 'pointer' }}
                >
                  ✕
                </button>
              </div>
              <img
                src={showCropPreview}
                alt="Source Crop"
                style={{ maxHeight: '180px', maxWidth: '100%', borderRadius: '4px' }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SummarySection;
