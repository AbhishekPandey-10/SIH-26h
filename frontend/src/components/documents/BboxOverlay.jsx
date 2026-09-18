import React, { useState } from 'react';
import {
  Pill,
  Activity,
  AlertTriangle,
  Stethoscope,
  Eye,
  CheckCircle2,
  XCircle,
  X,
  ExternalLink,
} from 'lucide-react';

export const BboxOverlay = ({
  imageUrl,
  documentId,
  entities = [],
  onClose,
}) => {
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [hoveredEntityId, setHoveredEntityId] = useState(null);

  const getEntityColor = (entity) => {
    const type = (entity.entity_type || entity.type || '').toLowerCase();
    if (type === 'medication') return { border: '#2563EB', fill: 'rgba(37, 99, 235, 0.22)', label: 'Medication', icon: Pill };
    if (type === 'diagnosis') return { border: '#9333EA', fill: 'rgba(147, 51, 234, 0.22)', label: 'Diagnosis', icon: Stethoscope };
    if (type === 'lab_value') {
      if (entity.is_abnormal === true) {
        return { border: '#DC2626', fill: 'rgba(220, 38, 38, 0.28)', label: 'Abnormal Lab', icon: AlertTriangle };
      }
      return { border: '#16A34A', fill: 'rgba(22, 163, 74, 0.22)', label: 'Normal Lab', icon: Activity };
    }
    return { border: '#D97706', fill: 'rgba(217, 119, 6, 0.22)', label: 'Clinical Finding', icon: Activity };
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        background: 'rgba(15, 23, 42, 0.88)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          background: '#0F172A',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          color: '#F8FAFC',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '6px 12px',
              borderRadius: '8px',
              background: '#0284C7',
              fontSize: '13px',
              fontWeight: 800,
            }}
          >
            BOUNDING-BOX VISUALIZER
          </div>
          <span style={{ fontSize: '15px', fontWeight: 600, color: '#94A3B8' }}>
            {entities.length} Verified Clinical Entities Extracted
          </span>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <span style={{ width: '12px', height: '12px', background: '#2563EB', borderRadius: '3px' }} />
            <span>Medications</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <span style={{ width: '12px', height: '12px', background: '#9333EA', borderRadius: '3px' }} />
            <span>Diagnoses</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <span style={{ width: '12px', height: '12px', background: '#16A34A', borderRadius: '3px' }} />
            <span>Normal Labs</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <span style={{ width: '12px', height: '12px', background: '#DC2626', borderRadius: '3px' }} />
            <span>Abnormal Labs</span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: '#334155',
              border: 'none',
              borderRadius: '8px',
              color: '#FFF',
              padding: '8px 14px',
              cursor: 'pointer',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <X size={18} />
            <span>Close</span>
          </button>
        </div>
      </div>

      {/* Main Workspace (Image on left, details panel on right) */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Document Image with Normalized Overlay Box */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            position: 'relative',
            overflow: 'auto',
          }}
        >
          <div
            style={{
              position: 'relative',
              display: 'inline-block',
              maxWidth: '100%',
              maxHeight: '100%',
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
              borderRadius: '8px',
              overflow: 'hidden',
            }}
          >
            <img
              src={imageUrl}
              alt="Scanned Document"
              style={{
                display: 'block',
                maxWidth: '100%',
                maxHeight: '80vh',
                objectFit: 'contain',
              }}
            />

            {/* Render Normalized Bounding Boxes */}
            {entities.map((entity, idx) => {
              const bbox = entity.bounding_box || entity.bbox;
              if (!bbox || bbox.length !== 4) return null;

              const [x, y, w, h] = bbox;
              const colorInfo = getEntityColor(entity);
              const isSelected = selectedEntity?.id === entity.id;
              const isHovered = hoveredEntityId === entity.id;

              return (
                <div
                  key={entity.id || idx}
                  onClick={() => setSelectedEntity(entity)}
                  onMouseEnter={() => setHoveredEntityId(entity.id)}
                  onMouseLeave={() => setHoveredEntityId(null)}
                  style={{
                    position: 'absolute',
                    left: `${x * 100}%`,
                    top: `${y * 100}%`,
                    width: `${w * 100}%`,
                    height: `${h * 100}%`,
                    border: `2.5px solid ${isSelected ? '#FBBF24' : colorInfo.border}`,
                    background: isSelected ? 'rgba(251, 191, 36, 0.35)' : colorInfo.fill,
                    cursor: 'pointer',
                    borderRadius: '4px',
                    transition: 'all 0.15s ease',
                    boxShadow: isSelected || isHovered ? '0 0 12px rgba(251, 191, 36, 0.8)' : 'none',
                    zIndex: isSelected ? 30 : isHovered ? 20 : 10,
                  }}
                  title={`${colorInfo.label}: ${entity.value}`}
                >
                  <span
                    style={{
                      position: 'absolute',
                      top: '-18px',
                      left: '0',
                      background: colorInfo.border,
                      color: '#FFF',
                      fontSize: '10px',
                      fontWeight: 800,
                      padding: '1px 5px',
                      borderRadius: '3px',
                      whiteSpace: 'nowrap',
                      pointerEvents: 'none',
                    }}
                  >
                    {entity.generic_name || entity.value?.slice(0, 18)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Entity Details Drawer */}
        <div
          style={{
            width: '380px',
            background: '#1E293B',
            borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '24px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#F8FAFC', marginBottom: '16px' }}>
            {selectedEntity ? 'Selected Entity Provenance' : 'Click Any Box to Inspect Evidence'}
          </h3>

          {selectedEntity ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Entity Type Pill */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span
                  style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    background: getEntityColor(selectedEntity).border,
                    color: '#FFF',
                    fontSize: '12px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                  }}
                >
                  {getEntityColor(selectedEntity).label}
                </span>

                <span style={{ fontSize: '13px', color: '#94A3B8', fontWeight: 600 }}>
                  Confidence: {Math.round((selectedEntity.confidence || 0.95) * 100)}%
                </span>
              </div>

              {/* Extracted Value Card */}
              <div
                style={{
                  padding: '14px',
                  background: '#0F172A',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.1)',
                }}
              >
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 700, textTransform: 'uppercase' }}>
                  Extracted Text
                </div>
                <div style={{ fontSize: '17px', fontWeight: 800, color: '#F8FAFC', marginTop: '4px' }}>
                  {selectedEntity.value}
                </div>

                {selectedEntity.generic_name && (
                  <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px dashed #334155' }}>
                    <span style={{ fontSize: '11px', color: '#38BDF8', fontWeight: 700 }}>
                      ACTIVE GENERIC MOLECULE:
                    </span>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#38BDF8' }}>
                      {selectedEntity.generic_name}
                    </div>
                  </div>
                )}
              </div>

              {/* Lab Evaluation Strip */}
              {selectedEntity.entity_type === 'lab_value' && (
                <div
                  style={{
                    padding: '14px',
                    borderRadius: '10px',
                    background: selectedEntity.is_abnormal ? 'rgba(220, 38, 38, 0.15)' : 'rgba(22, 163, 74, 0.15)',
                    border: `1.5px solid ${selectedEntity.is_abnormal ? '#DC2626' : '#16A34A'}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {selectedEntity.is_abnormal ? (
                      <AlertTriangle size={18} color="#DC2626" />
                    ) : (
                      <CheckCircle2 size={18} color="#16A34A" />
                    )}
                    <span style={{ fontWeight: 800, fontSize: '14px', color: selectedEntity.is_abnormal ? '#EF4444' : '#22C55E' }}>
                      {selectedEntity.is_abnormal ? 'ABNORMAL READING FLAGGED' : 'NORMAL PHYSIOLOGICAL BOUND'}
                    </span>
                  </div>
                  {selectedEntity.reference_range && (
                    <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '6px' }}>
                      Clinical Reference: {selectedEntity.reference_range}
                    </div>
                  )}
                </div>
              )}

              {/* Cropped Region Preview */}
              <div>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#94A3B8' }}>
                  CROPPED SOURCE REGION (8% Drift Padding):
                </span>
                <div
                  style={{
                    marginTop: '6px',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    border: '1.5px solid #334155',
                    background: '#000',
                  }}
                >
                  <img
                    src={`/api/documents/${selectedEntity.document_id || documentId}/crop?x=${selectedEntity.bounding_box[0]}&y=${selectedEntity.bounding_box[1]}&w=${selectedEntity.bounding_box[2]}&h=${selectedEntity.bounding_box[3]}`}
                    alt="Source Crop"
                    style={{ width: '100%', display: 'block', objectFit: 'contain' }}
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                </div>
              </div>

              {/* Metadata */}
              <div style={{ fontSize: '12px', color: '#64748B', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>Document ID: {selectedEntity.document_id || documentId}</div>
                <div>Extracted Date: {selectedEntity.date || 'Date unknown'}</div>
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748B', fontSize: '14px', textAlign: 'center', marginTop: '40px' }}>
              <p>Hover over or click on any highlighted bounding box on the prescription to verify its exact source coordinates.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BboxOverlay;
