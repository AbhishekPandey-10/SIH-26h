import React, { useState } from 'react';
import { VerificationBadge } from './VerificationBadge';
import AskBackPanel from './AskBackPanel';
import ClickToSource from './ClickToSource';
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
  Split,
  User,
  CheckCircle2,
  HelpCircle,
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

  // Conflicting Resolution State
  const [isResolvingConflict, setIsResolvingConflict] = useState(false);
  const [customResolutionText, setCustomResolutionText] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

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

  // Doctor resolves conflicting field
  const handleResolveConflict = async (choice, value) => {
    setIsResolvingConflict(true);
    try {
      const res = await fetch(`/api/summary/${sessionId}/resolve/${field.field_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution_choice: choice,
          resolved_value: value,
          doctor_id: 'doc_opd_01',
          doctor_note: `Discrepancy resolved by physician preferring ${choice}.`,
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        setShowCustomInput(false);
        if (onFieldUpdated) {
          onFieldUpdated(updated);
        }
      }
    } catch (err) {
      console.warn('[SummarySection] Conflict resolution error:', err);
    } finally {
      setIsResolvingConflict(false);
    }
  };

  const isDocEdited = field.verification === 'doctor_edited';
  const isConflicting = field.verification === 'conflicting';

  // Extract document vs patient values for split-view
  const docSource = field.sources?.find((s) => s.type === 'document');
  const patientSource = field.sources?.find((s) => s.type === 'transcript');
  const docValue = field.document_value || docSource?.entity_value || docSource?.snippet || 'Document value';
  const patientValue = field.patient_value || patientSource?.snippet || 'Patient verbal report';

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '14px',
        border: isConflicting
          ? '2px solid #F59E0B'
          : isDocEdited
          ? '2px solid #C084FC'
          : '1.5px solid #E2E8F0',
        boxShadow: isConflicting
          ? '0 4px 16px rgba(245, 158, 11, 0.12)'
          : '0 2px 8px rgba(0,0,0,0.04)',
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
          background: isConflicting ? '#FFFBEB' : isDocEdited ? '#FAF5FF' : '#F8FAFC',
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
                  {polypharmacyAlerts.map((a) => (typeof a === 'string' ? a : a.message)).join(' • ')}
                </div>
              </div>
            </div>
          )}

          {/* TASK 1 ITEM 5: CONFLICTING DATA SPLIT-VIEW */}
          {isConflicting && (
            <div
              style={{
                marginBottom: '20px',
                padding: '16px',
                background: '#FFFDF5',
                borderRadius: '12px',
                border: '1.5px solid #FCD34D',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '12px',
                  color: '#B45309',
                  fontWeight: 800,
                  fontSize: '14px',
                }}
              >
                <Split size={18} />
                <span>Conflicting Evidence Detected: Discrepancy Between Document & Verbal Report</span>
              </div>

              {/* Side-by-Side Comparison Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '16px',
                  marginBottom: '14px',
                }}
              >
                {/* Column 1: Document Value */}
                <div
                  style={{
                    padding: '14px',
                    background: '#FFFFFF',
                    borderRadius: '10px',
                    border: '1.5px solid #86EFAC',
                  }}
                >
                  <div style={{ fontSize: '11px', fontWeight: 800, color: '#16A34A', textTransform: 'uppercase' }}>
                    📄 Scanned Document Record:
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '4px' }}>
                    {docValue}
                  </div>
                  {docSource && (
                    <div style={{ marginTop: '8px' }}>
                      <ClickToSource
                        singleSource={docSource}
                        customLabel="Inspect Original Crop"
                        inline
                      />
                    </div>
                  )}
                </div>

                {/* Column 2: Patient Verbal Value */}
                <div
                  style={{
                    padding: '14px',
                    background: '#FFFFFF',
                    borderRadius: '10px',
                    border: '1.5px solid #93C5FD',
                  }}
                >
                  <div style={{ fontSize: '11px', fontWeight: 800, color: '#2563EB', textTransform: 'uppercase' }}>
                    🎙️ Patient Stated in Interview:
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '4px' }}>
                    {patientValue}
                  </div>
                  {patientSource && (
                    <div style={{ marginTop: '8px' }}>
                      <ClickToSource
                        singleSource={patientSource}
                        customLabel="Inspect Q&A Transcript"
                        inline
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Doctor Resolution Buttons */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '10px',
                  paddingTop: '10px',
                  borderTop: '1px solid #FEF3C7',
                }}
              >
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#92400E' }}>
                  Doctor Resolution:
                </span>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => handleResolveConflict('use_document', docValue)}
                    disabled={isResolvingConflict}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '8px',
                      border: '1.5px solid #16A34A',
                      background: '#F0FDF4',
                      color: '#166534',
                      fontWeight: 700,
                      fontSize: '12px',
                      cursor: 'pointer',
                    }}
                  >
                    ✓ Use document value
                  </button>

                  <button
                    onClick={() => handleResolveConflict('use_patient', patientValue)}
                    disabled={isResolvingConflict}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '8px',
                      border: '1.5px solid #2563EB',
                      background: '#EFF6FF',
                      color: '#1E40AF',
                      fontWeight: 700,
                      fontSize: '12px',
                      cursor: 'pointer',
                    }}
                  >
                    ✓ Use patient value
                  </button>

                  <button
                    onClick={() => setShowCustomInput(!showCustomInput)}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '8px',
                      border: '1.5px solid #64748B',
                      background: '#F8FAFC',
                      color: '#334155',
                      fontWeight: 700,
                      fontSize: '12px',
                      cursor: 'pointer',
                    }}
                  >
                    ✎ Write custom
                  </button>
                </div>
              </div>

              {/* Custom Resolution Input */}
              {showCustomInput && (
                <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    placeholder="Enter physician reconciled value..."
                    value={customResolutionText}
                    onChange={(e) => setCustomResolutionText(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1.5px solid #CBD5E1',
                      fontSize: '14px',
                    }}
                  />
                  <button
                    onClick={() => handleResolveConflict('custom', customResolutionText || docValue)}
                    disabled={!customResolutionText.trim()}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '8px',
                      border: 'none',
                      background: '#0F172A',
                      color: '#FFF',
                      fontWeight: 700,
                      fontSize: '13px',
                      cursor: 'pointer',
                    }}
                  >
                    Save Resolution
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Standard Content Display / Inline Editing */}
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

          {/* TASK 1 ITEM 1: CLICK-TO-SOURCE EVIDENCE PROVENANCE */}
          {field.sources && field.sources.length > 0 && (
            <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid #F1F5F9' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, color: '#94A3B8', textTransform: 'uppercase' }}>
                TRACEABLE EVIDENCE CITATIONS ({field.sources.length} sources):
              </span>
              <div style={{ marginTop: '8px' }}>
                <ClickToSource sources={field.sources} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SummarySection;
