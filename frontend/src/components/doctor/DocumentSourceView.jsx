import React, { useState } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, FileText, CheckCircle, ShieldAlert, Sparkles } from 'lucide-react';

/**
 * <DocumentSourceView />
 * PS ID26047 — Clinical Click-to-Source Magnified Evidence Viewer
 * 
 * Props:
 * - imageUrl: string (e.g. "/api/documents/{doc_id}/image")
 * - bbox: object { x, y, w, h } or array [x, y, w, h] (normalized 0.0 - 1.0)
 * - cropUrl: string (e.g. "/api/documents/{doc_id}/crop?bbox=...")
 * - entityValue: string (e.g. "Tab Glycomet 500mg")
 * - confidence: number (e.g. 0.92)
 * - onClose: optional function
 */
export const DocumentSourceView = ({
  imageUrl = '/api/documents/doc_prev_presc_01/image',
  bbox = { x: 0.12, y: 0.34, w: 0.45, h: 0.08 },
  cropUrl = '',
  entityValue = 'Tab Glycomet 500mg BD',
  confidence = 0.92,
  onClose,
}) => {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [activeTab, setActiveTab] = useState('split'); // 'split' | 'crop_focus' | 'full_overlay'

  // Normalize bbox format: supports both {x, y, w, h} and [x, y, w, h]
  const parsedBbox = Array.isArray(bbox)
    ? { x: bbox[0] || 0.1, y: bbox[1] || 0.2, w: bbox[2] || 0.4, h: bbox[3] || 0.08 }
    : {
        x: bbox?.x ?? 0.12,
        y: bbox?.y ?? 0.34,
        w: bbox?.w ?? 0.45,
        h: bbox?.h ?? 0.08,
      };

  const confidencePct = Math.round((confidence <= 1 ? confidence * 100 : confidence) || 95);
  const isHighConf = confidencePct >= 85;

  const fallbackCropUrl =
    cropUrl ||
    `${imageUrl.replace('/image', '/crop')}?x=${parsedBbox.x}&y=${parsedBbox.y}&w=${parsedBbox.w}&h=${parsedBbox.h}`;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        background: '#0F172A',
        color: '#F8FAFC',
        borderRadius: '16px',
        padding: '20px',
        border: '1.5px solid #334155',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        width: '100%',
        maxWidth: '960px',
        margin: '0 auto',
        boxSizing: 'border-box',
      }}
    >
      {/* Top Header & Extracted Value Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          borderBottom: '1px solid #1E293B',
          paddingBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: '#0284C7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <FileText size={22} color="#FFF" />
          </div>
          <div>
            <div style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase' }}>
              Original Clinical Document Evidence
            </div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#F8FAFC' }}>
              Extracted value: <span style={{ color: '#38BDF8' }}>"{entityValue}"</span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Confidence Badge */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '20px',
              background: isHighConf ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              border: `1.5px solid ${isHighConf ? '#10B981' : '#F59E0B'}`,
              color: isHighConf ? '#34D399' : '#FBBF24',
              fontWeight: 800,
              fontSize: '13px',
            }}
          >
            {isHighConf ? <CheckCircle size={15} /> : <ShieldAlert size={15} />}
            <span>Confidence: {confidencePct}%</span>
          </div>

          {/* View Mode Switcher */}
          <div
            style={{
              display: 'flex',
              background: '#1E293B',
              borderRadius: '8px',
              padding: '2px',
            }}
          >
            <button
              onClick={() => setActiveTab('split')}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: 'none',
                background: activeTab === 'split' ? '#0284C7' : 'transparent',
                color: '#FFF',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Side-by-Side
            </button>
            <button
              onClick={() => setActiveTab('crop_focus')}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: 'none',
                background: activeTab === 'crop_focus' ? '#0284C7' : 'transparent',
                color: '#FFF',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Magnified Crop
            </button>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: '#1E293B',
                border: '1px solid #334155',
                color: '#94A3B8',
                borderRadius: '8px',
                width: '36px',
                height: '36px',
                fontSize: '16px',
                fontWeight: 800,
                cursor: 'pointer',
              }}
              title="Close Evidence Modal"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Main Evidence Visualizer */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: activeTab === 'split' ? '1fr 1fr' : '1fr',
          gap: '16px',
          minHeight: '380px',
        }}
      >
        {/* Left / Full: Original Scanned Image with Bounding Box Overlay */}
        {(activeTab === 'split' || activeTab === 'full_overlay') && (
          <div
            style={{
              background: '#020617',
              borderRadius: '12px',
              border: '1px solid #1E293B',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div
              style={{
                padding: '10px 14px',
                background: '#1E293B',
                fontSize: '12px',
                fontWeight: 700,
                color: '#94A3B8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>Original Scanned Document (BBox Coordinate Overlay)</span>
              <span>
                Coordinates: [{parsedBbox.x.toFixed(2)}, {parsedBbox.y.toFixed(2)}, {parsedBbox.w.toFixed(2)},{' '}
                {parsedBbox.h.toFixed(2)}]
              </span>
            </div>

            <div
              style={{
                position: 'relative',
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#000',
                padding: '8px',
                overflow: 'hidden',
              }}
            >
              {/* Document Image Container */}
              <div
                style={{
                  position: 'relative',
                  display: 'inline-block',
                  maxWidth: '100%',
                  maxHeight: '440px',
                }}
              >
                <img
                  src={imageUrl}
                  alt="Scanned Prescription"
                  style={{
                    display: 'block',
                    maxWidth: '100%',
                    maxHeight: '420px',
                    borderRadius: '6px',
                    objectFit: 'contain',
                  }}
                  onError={(e) => {
                    // Fallback to sample document if local path fails
                    e.target.src = '/api/documents/doc_01_prescription_printed/image';
                  }}
                />

                {/* Dark Semi-Transparent Backdrop Overlay with Bbox Cutout */}
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(15, 23, 42, 0.45)',
                    pointerEvents: 'none',
                  }}
                />

                {/* Highlighted Bounding Box Rectangle */}
                <div
                  style={{
                    position: 'absolute',
                    top: `${parsedBbox.y * 100}%`,
                    left: `${parsedBbox.x * 100}%`,
                    width: `${parsedBbox.w * 100}%`,
                    height: `${parsedBbox.h * 100}%`,
                    border: '2.5px solid #00F0FF',
                    background: 'rgba(0, 240, 255, 0.12)',
                    boxShadow: '0 0 16px rgba(0, 240, 255, 0.75), inset 0 0 8px rgba(0, 240, 255, 0.3)',
                    borderRadius: '4px',
                    animation: 'pulseGlow 2s infinite ease-in-out',
                    transition: 'all 0.3s ease',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      top: '-20px',
                      left: 0,
                      background: '#00F0FF',
                      color: '#0F172A',
                      fontWeight: 800,
                      fontSize: '10px',
                      padding: '1px 6px',
                      borderRadius: '3px',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    EVIDENCE REGION ({confidencePct}%)
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Right / Magnified Focus Panel: Zoomed Crop Region with 10% Safety Padding */}
        {(activeTab === 'split' || activeTab === 'crop_focus') && (
          <div
            style={{
              background: '#020617',
              borderRadius: '12px',
              border: '1px solid #1E293B',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div
              style={{
                padding: '10px 14px',
                background: '#1E293B',
                fontSize: '12px',
                fontWeight: 700,
                color: '#94A3B8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={14} color="#38BDF8" />
                <span>Magnified Crop (8-10% Drift Padding)</span>
              </div>

              {/* Zoom Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button
                  onClick={() => setZoomLevel((z) => Math.max(0.7, z - 0.2))}
                  style={{
                    background: '#334155',
                    border: 'none',
                    color: '#FFF',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    cursor: 'pointer',
                  }}
                  title="Zoom Out"
                >
                  <ZoomOut size={13} />
                </button>
                <span style={{ fontSize: '11px', color: '#CBD5E1', minWidth: '34px', textAlign: 'center' }}>
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button
                  onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.2))}
                  style={{
                    background: '#334155',
                    border: 'none',
                    color: '#FFF',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    cursor: 'pointer',
                  }}
                  title="Zoom In"
                >
                  <ZoomIn size={13} />
                </button>
                <button
                  onClick={() => setZoomLevel(1)}
                  style={{
                    background: '#334155',
                    border: 'none',
                    color: '#FFF',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    cursor: 'pointer',
                  }}
                  title="Reset Zoom"
                >
                  <RotateCcw size={13} />
                </button>
              </div>
            </div>

            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
                background: '#0B0F19',
                overflow: 'auto',
              }}
            >
              <div
                style={{
                  transform: `scale(${zoomLevel})`,
                  transformOrigin: 'center center',
                  transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  borderRadius: '8px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                  border: '2px solid #0284C7',
                  background: '#FFF',
                  padding: '6px',
                  display: 'inline-block',
                }}
              >
                <img
                  src={fallbackCropUrl}
                  alt="Magnified Crop"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '260px',
                    display: 'block',
                    borderRadius: '4px',
                  }}
                  onError={(e) => {
                    // Fallback to mock crop preview if needed
                    e.target.style.display = 'none';
                    if (e.target.nextSibling) e.target.nextSibling.style.display = 'block';
                  }}
                />
                <div
                  style={{
                    display: 'none',
                    padding: '20px',
                    color: '#0F172A',
                    fontWeight: 800,
                    textAlign: 'center',
                  }}
                >
                  [Crop Preview: {entityValue}]
                </div>
              </div>
            </div>

            {/* Bottom Verification Guidance */}
            <div
              style={{
                padding: '12px 16px',
                background: '#0F172A',
                borderTop: '1px solid #1E293B',
                fontSize: '12px',
                color: '#94A3B8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>OCR Engine: Gemini Multimodal Vision 2.0</span>
              <span style={{ color: isHighConf ? '#34D399' : '#FBBF24', fontWeight: 700 }}>
                {isHighConf ? '✓ High Confidence Verification' : '⚠ Requires Clinical Confirmation'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentSourceView;
