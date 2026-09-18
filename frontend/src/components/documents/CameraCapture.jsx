import React, { useState, useRef, useEffect } from 'react';
import KioskButton from '../kiosk/KioskButton';
import KioskCard from '../kiosk/KioskCard';
import {
  Camera,
  RotateCw,
  Trash2,
  Upload,
  CheckCircle,
  X,
  FileText,
  AlertCircle,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

export const CameraCapture = ({
  sessionId,
  language = 'hi',
  onScanComplete,
  onCancel,
}) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const [stream, setStream] = useState(null);
  const [capturedPages, setCapturedPages] = useState([]); // { id, dataUrl, rotation, fileType, pageNumber }
  const [activePageIndex, setActivePageIndex] = useState(0);
  const [isCapturing, setIsCapturing] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [documentType, setDocumentType] = useState('prescription'); // prescription | lab | discharge

  // Start Camera Stream
  useEffect(() => {
    let activeStream = null;

    async function startCamera() {
      try {
        setCameraError(null);
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
        activeStream = mediaStream;
        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      } catch (err) {
        console.warn('[CameraCapture] Camera access failed or denied:', err);
        setCameraError(
          'कैमरा शुरू करने में असमर्थ। कृपया नीचे दिए गए "गैलरी से अपलोड करें" बटन का उपयोग करें।'
        );
      }
    }

    startCamera();

    return () => {
      if (activeStream) {
        activeStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Capture Frame from Video
  const handleCapture = () => {
    if (!videoRef.current || !canvasRef.current) return;
    setIsCapturing(true);

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const newPage = {
      id: `page_${Date.now()}`,
      dataUrl,
      rotation: 0,
      fileType: documentType,
      pageNumber: capturedPages.length + 1,
    };

    setCapturedPages((prev) => [...prev, newPage]);
    setActivePageIndex(capturedPages.length);

    setTimeout(() => setIsCapturing(false), 200);
  };

  // Upload Existing File(s) from Device
  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    files.forEach((file, index) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const newPage = {
          id: `file_${Date.now()}_${index}`,
          dataUrl: event.target.result,
          rotation: 0,
          fileType: documentType,
          pageNumber: capturedPages.length + index + 1,
        };
        setCapturedPages((prev) => [...prev, newPage]);
      };
      reader.readAsDataURL(file);
    });
  };

  // Rotate Page by 90 degrees
  const handleRotatePage = (index) => {
    setCapturedPages((prev) =>
      prev.map((page, i) => {
        if (i !== index) return page;
        const newRot = (page.rotation + 90) % 360;

        // Apply rotation to internal image canvas
        const img = new Image();
        img.src = page.dataUrl;
        img.onload = () => {
          const c = document.createElement('canvas');
          if (newRot === 90 || newRot === 270) {
            c.width = img.height;
            c.height = img.width;
          } else {
            c.width = img.width;
            c.height = img.height;
          }
          const ctx = c.getContext('2d');
          ctx.translate(c.width / 2, c.height / 2);
          ctx.rotate((newRot * Math.PI) / 180);
          ctx.drawImage(img, -img.width / 2, -img.height / 2);
        };

        return { ...page, rotation: newRot };
      })
    );
  };

  // Delete Page
  const handleDeletePage = (index) => {
    setCapturedPages((prev) => {
      const filtered = prev.filter((_, i) => i !== index);
      return filtered.map((p, idx) => ({ ...p, pageNumber: idx + 1 }));
    });
    if (activePageIndex >= capturedPages.length - 1) {
      setActivePageIndex(Math.max(0, capturedPages.length - 2));
    }
  };

  // Finish Scanning & Trigger Batch Upload/OCR
  const handleDoneScanning = () => {
    if (!capturedPages.length) return;
    if (onScanComplete) {
      onScanComplete(capturedPages);
    }
  };

  const isHindi = language === 'hi';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: '#0F172A',
        color: '#F8FAFC',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Top Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 24px',
          background: 'rgba(15, 23, 42, 0.95)',
          borderBottom: '1.5px solid rgba(255, 255, 255, 0.1)',
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
            <Camera size={24} color="#FFF" />
          </div>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0 }}>
              {isHindi ? 'दस्तावेज़ स्कैनर (कागजी पर्चे व लैब रिपोर्ट)' : 'OPD Document Scanner (Camera OCR)'}
            </h2>
            <span style={{ fontSize: '13px', color: '#94A3B8' }}>
              {isHindi
                ? 'पर्चे को सीधे व साफ रखें — दवाइयां व जांच रिपोर्ट स्वतः पहचानी जाएंगी'
                : 'Align document flat in frame — Gemini extracts medicines & lab values'}
            </span>
          </div>
        </div>

        {/* Document Type Selector & Close */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', background: '#1E293B', borderRadius: '8px', padding: '4px' }}>
            <button
              onClick={() => setDocumentType('prescription')}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                background: documentType === 'prescription' ? '#2563EB' : 'transparent',
                color: '#FFF',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {isHindi ? 'पर्चा (Prescription)' : 'Prescription'}
            </button>
            <button
              onClick={() => setDocumentType('lab')}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                background: documentType === 'lab' ? '#2563EB' : 'transparent',
                color: '#FFF',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {isHindi ? 'लैब रिपोर्ट (Lab Test)' : 'Lab Report'}
            </button>
            <button
              onClick={() => setDocumentType('discharge')}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                background: documentType === 'discharge' ? '#2563EB' : 'transparent',
                color: '#FFF',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {isHindi ? 'डिस्चार्ज सारांश (Discharge)' : 'Discharge'}
            </button>
          </div>

          <button
            onClick={onCancel}
            style={{
              background: '#334155',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#FFF',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontWeight: 600,
            }}
          >
            <X size={20} />
            <span>{isHindi ? 'रद्द करें' : 'Cancel'}</span>
          </button>
        </div>
      </div>

      {/* Main Viewfinder Canvas */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          background: '#000',
        }}
      >
        {/* Live Camera Viewfinder */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            transform: 'scaleX(1)',
          }}
        />

        {/* Hidden Canvas for Frame Grab */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* Document Frame Guide (Target Rect) */}
        <div
          style={{
            position: 'absolute',
            width: '78%',
            maxWidth: '720px',
            height: '75%',
            border: '2.5px dashed #0284C7',
            borderRadius: '16px',
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.45)',
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38BDF8', fontSize: '12px', fontWeight: 700 }}>
            <span>┌ A4 DOCUMENT ALIGNMENT</span>
            <span>┐</span>
          </div>
          <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.75)', fontSize: '14px', fontWeight: 600 }}>
            {isHindi ? 'दस्तावेज़ को इस चौकोर बॉक्स के अंदर रखें' : 'Place document squarely within dashed box'}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38BDF8', fontSize: '12px', fontWeight: 700 }}>
            <span>└</span>
            <span>┘</span>
          </div>
        </div>

        {/* Camera Error / Fallback Banner */}
        {cameraError && (
          <div
            style={{
              position: 'absolute',
              top: '24px',
              background: 'rgba(220, 38, 38, 0.92)',
              color: '#FFF',
              padding: '12px 20px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              maxWidth: '600px',
            }}
          >
            <AlertCircle size={24} />
            <span style={{ fontSize: '14px', fontWeight: 600 }}>{cameraError}</span>
          </div>
        )}

        {/* Flash Effect on Capture */}
        {isCapturing && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: '#FFF',
              opacity: 0.8,
              transition: 'opacity 0.2s',
            }}
          />
        )}
      </div>

      {/* Captured Pages Strip (Bottom) */}
      {capturedPages.length > 0 && (
        <div
          style={{
            background: '#1E293B',
            padding: '12px 24px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            overflowX: 'auto',
            borderTop: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#94A3B8', whiteSpace: 'nowrap' }}>
            {isHindi ? `स्कैन किए गए पृष्ठ (${capturedPages.length}):` : `Pages (${capturedPages.length}):`}
          </span>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {capturedPages.map((page, idx) => (
              <div
                key={page.id}
                style={{
                  position: 'relative',
                  width: '64px',
                  height: '80px',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  border: idx === activePageIndex ? '2.5px solid #0284C7' : '1px solid #475569',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
                onClick={() => setActivePageIndex(idx)}
              >
                <img
                  src={page.dataUrl}
                  alt={`Page ${page.pageNumber}`}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    transform: `rotate(${page.rotation}deg)`,
                  }}
                />
                <span
                  style={{
                    position: 'absolute',
                    bottom: '2px',
                    left: '2px',
                    background: 'rgba(0,0,0,0.7)',
                    padding: '2px 4px',
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: 800,
                  }}
                >
                  P{page.pageNumber}
                </span>

                {/* Per-Page Controls (Rotate & Delete) */}
                <div
                  style={{
                    position: 'absolute',
                    top: '2px',
                    right: '2px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                  }}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRotatePage(idx);
                    }}
                    title="Rotate 90°"
                    style={{
                      background: 'rgba(0,0,0,0.75)',
                      border: 'none',
                      color: '#FFF',
                      borderRadius: '4px',
                      padding: '3px',
                      cursor: 'pointer',
                    }}
                  >
                    <RotateCw size={12} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeletePage(idx);
                    }}
                    title="Delete Page"
                    style={{
                      background: 'rgba(220, 38, 38, 0.85)',
                      border: 'none',
                      color: '#FFF',
                      borderRadius: '4px',
                      padding: '3px',
                      cursor: 'pointer',
                    }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom Controls Bar */}
      <div
        style={{
          padding: '20px 24px',
          background: '#0F172A',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        {/* Gallery Upload Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />
        <KioskButton
          variant="secondary"
          size="md"
          icon={<Upload size={20} />}
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
        >
          {isHindi ? 'गैलरी से अपलोड करें' : 'Upload from Device'}
        </KioskButton>

        {/* Centered Big Shutter Button */}
        <button
          onClick={handleCapture}
          style={{
            width: '76px',
            height: '76px',
            borderRadius: '50%',
            background: '#FFF',
            border: '6px solid #0284C7',
            boxShadow: '0 0 20px rgba(2, 132, 199, 0.5)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.1s ease',
          }}
          onMouseDown={(e) => (e.currentTarget.style.transform = 'scale(0.92)')}
          onMouseUp={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              background: '#0284C7',
            }}
          />
        </button>

        {/* Done Scanning Button */}
        <KioskButton
          variant="primary"
          size="md"
          disabled={capturedPages.length === 0}
          icon={<CheckCircle size={20} />}
          onClick={handleDoneScanning}
        >
          {isHindi
            ? `स्कैन पूरा करें (${capturedPages.length}) →`
            : `Done Scanning (${capturedPages.length}) →`}
        </KioskButton>
      </div>
    </div>
  );
};

export default CameraCapture;
