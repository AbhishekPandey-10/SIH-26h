import React, { useState, useEffect } from 'react';
import KioskCard from '../kiosk/KioskCard';
import ProgressBar from '../kiosk/ProgressBar';
import { Loader2, CheckCircle2, AlertCircle, FileSearch, Sparkles } from 'lucide-react';

export const ScanProgress = ({
  sessionId,
  documents = [], // [{ id, pageNumber, fileType }]
  onAllCompleted,
  language = 'hi',
}) => {
  const [docStatuses, setDocStatuses] = useState(() => {
    const initial = {};
    documents.forEach((d) => {
      initial[d.id] = {
        status: 'processing',
        progress: 0.15,
        message: 'अपलोड व विश्लेषण प्रारंभ...',
      };
    });
    return initial;
  });

  // Connect to WebSocket /ws/scan-status/{session_id}
  useEffect(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/scan-status/${sessionId}`;

    let socket = null;
    try {
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        console.log('[ScanProgress] Connected to scan status stream:', wsUrl);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.document_id) {
            setDocStatuses((prev) => ({
              ...prev,
              [data.document_id]: {
                status: data.status,
                progress: data.progress !== undefined ? data.progress : prev[data.document_id]?.progress || 0.5,
                message: data.message || getStatusLabel(data.status),
              },
            }));
          }
        } catch (e) {
          console.warn('[ScanProgress] WebSocket parse error:', e);
        }
      };

      socket.onerror = (err) => {
        console.warn('[ScanProgress] WebSocket stream warning:', err);
      };
    } catch (err) {
      console.warn('[ScanProgress] WebSocket init error:', err);
    }

    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, [sessionId]);

  // Status text helper
  const getStatusLabel = (status) => {
    switch (status) {
      case 'uploading':
        return language === 'hi' ? 'दस्तावेज़ सुरक्षित अपलोड हो रहा है...' : 'Uploading file...';
      case 'processing':
        return language === 'hi' ? 'Gemini 2.0 विज़न मॉडल विश्लेषण कर रहा है...' : 'Gemini Vision AI analyzing layout...';
      case 'extracting':
        return language === 'hi' ? 'दवाइयां व टेस्ट परिणाम निकाले जा रहे हैं...' : 'Extracting clinical entities & lab values...';
      case 'done':
        return language === 'hi' ? 'विश्लेषण पूर्ण! सभी दवाइयां पहचानी गईं।' : 'Extraction complete!';
      case 'error':
        return language === 'hi' ? 'त्रुटि: पुनः प्रयास करें।' : 'Extraction error';
      default:
        return status;
    }
  };

  // Check overall completion
  const allDone =
    documents.length > 0 &&
    documents.every((d) => {
      const s = docStatuses[d.id]?.status;
      return s === 'done' || s === 'extracted';
    });

  useEffect(() => {
    if (allDone && onAllCompleted) {
      const timer = setTimeout(() => {
        onAllCompleted();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [allDone, onAllCompleted]);

  return (
    <div style={{ width: '100%', maxWidth: '720px', margin: '0 auto', padding: '24px 20px' }}>
      <KioskCard padding="32px">
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '20px',
              background: '#EFF6FF',
              color: '#0284C7',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}
          >
            {allDone ? (
              <CheckCircle2 size={36} color="#059669" />
            ) : (
              <Sparkles size={36} color="#0284C7" />
            )}
          </div>

          <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
            {allDone
              ? language === 'hi'
                ? 'दस्तावेज़ सफलतापूर्वक विश्लेषित!'
                : 'Documents Successfully Analyzed!'
              : language === 'hi'
              ? 'AI द्वारा दस्तावेज़ विश्लेषण प्रगति पर...'
              : 'AI Document Intelligence in Progress...'}
          </h2>

          <p style={{ fontSize: '15px', color: '#64748B', maxWidth: '520px', margin: '0 auto' }}>
            {language === 'hi'
              ? 'कागजी पर्चों की लिखावट व टेस्ट रिपोर्ट से दवाइयों का नाम, खुराक और तारीख निकाली जा रही है।'
              : 'Extracting medications, active generic molecules, and abnormal lab flags with verified bounding boxes.'}
          </p>
        </div>

        {/* Per-Document Progress List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {documents.map((doc, idx) => {
            const current = docStatuses[doc.id] || { status: 'processing', progress: 0.2 };
            const isFinished = current.status === 'done' || current.status === 'extracted';
            const isError = current.status === 'error';

            return (
              <div
                key={doc.id}
                style={{
                  padding: '18px 20px',
                  background: '#F8FAFC',
                  borderRadius: '14px',
                  border: '1.5px solid #E2E8F0',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <FileSearch size={20} color="#0284C7" />
                    <span style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>
                      {language === 'hi' ? `पृष्ठ ${doc.pageNumber || idx + 1}: ${doc.fileType || 'पर्चा'}` : `Page ${doc.pageNumber || idx + 1}: ${doc.fileType || 'Prescription'}`}
                    </span>
                  </div>

                  <span
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: isFinished ? '#059669' : isError ? '#DC2626' : '#0284C7',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    {isFinished ? (
                      <>
                        <CheckCircle2 size={16} />
                        <span>100%</span>
                      </>
                    ) : isError ? (
                      <>
                        <AlertCircle size={16} />
                        <span>Error</span>
                      </>
                    ) : (
                      <>
                        <Loader2 size={16} className="spin" />
                        <span>{Math.round((current.progress || 0.4) * 100)}%</span>
                      </>
                    )}
                  </span>
                </div>

                <ProgressBar
                  progress={Math.round((current.progress || 0.3) * 100)}
                  color={isFinished ? 'green' : isError ? 'red' : 'primary'}
                />

                <div
                  style={{
                    fontSize: '13px',
                    color: '#64748B',
                    marginTop: '8px',
                    fontWeight: 500,
                  }}
                >
                  {current.message || getStatusLabel(current.status)}
                </div>
              </div>
            );
          })}
        </div>
      </KioskCard>
    </div>
  );
};

export default ScanProgress;
