import React, { useState } from 'react';
import CameraCapture from './CameraCapture';
import ScanProgress from './ScanProgress';
import DocumentList from './DocumentList';
import KioskButton from '../kiosk/KioskButton';
import { ArrowLeft } from 'lucide-react';

export const DocumentWorkflow = ({
  sessionId,
  language = 'hi',
  onBack,
}) => {
  const [stage, setStage] = useState('capture'); // 'capture' | 'progress' | 'list'
  const [processedDocs, setProcessedDocs] = useState([]);

  // Converts Base64 Data URL to Blob for multipart upload
  const dataUrlToBlob = (dataUrl) => {
    const arr = dataUrl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new Blob([u8arr], { type: mime });
  };

  const handleScanComplete = async (capturedPages) => {
    if (!capturedPages.length) return;
    setStage('progress');

    const uploadedList = [];

    for (let i = 0; i < capturedPages.length; i++) {
      const page = capturedPages[i];
      try {
        const blob = dataUrlToBlob(page.dataUrl);
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('page_number', page.pageNumber.toString());
        formData.append('file_type', page.fileType || 'prescription');
        formData.append('file', blob, `page_${page.pageNumber}.jpg`);

        // 1. Upload
        const uploadRes = await fetch('/api/documents/upload', {
          method: 'POST',
          body: formData,
        });

        if (uploadRes.ok) {
          const uploadData = await uploadRes.json();
          uploadedList.push({
            id: uploadData.document_id,
            pageNumber: page.pageNumber,
            fileType: page.fileType,
          });

          // 2. Trigger async OCR processing
          fetch(`/api/documents/process/${uploadData.document_id}`, {
            method: 'POST',
          }).catch((err) => console.warn('[DocumentWorkflow] Process trigger warning:', err));
        }
      } catch (err) {
        console.error('[DocumentWorkflow] Error uploading page:', err);
      }
    }

    setProcessedDocs(uploadedList);
  };

  if (stage === 'capture') {
    return (
      <CameraCapture
        sessionId={sessionId}
        language={language}
        onScanComplete={handleScanComplete}
        onCancel={onBack}
      />
    );
  }

  if (stage === 'progress') {
    return (
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '24px 20px' }}>
        <ScanProgress
          sessionId={sessionId}
          documents={processedDocs}
          language={language}
          onAllCompleted={() => setStage('list')}
        />
      </div>
    );
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          maxWidth: '960px',
          width: '100%',
          margin: '0 auto',
          padding: '20px 20px 0',
          display: 'flex',
          justifyContent: 'flex-start',
        }}
      >
        <KioskButton
          variant="secondary"
          size="sm"
          icon={<ArrowLeft size={18} />}
          onClick={onBack}
        >
          {language === 'hi' ? '← मुख्य डैशबोर्ड पर लौटें' : '← Back to Dashboard'}
        </KioskButton>
      </div>

      <DocumentList
        sessionId={sessionId}
        language={language}
        onScanMore={() => setStage('capture')}
      />
    </div>
  );
};

export default DocumentWorkflow;
