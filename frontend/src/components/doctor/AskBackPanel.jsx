import React, { useState } from 'react';
import {
  MessageSquare,
  Send,
  Loader2,
  CheckCircle2,
  X,
  User,
  Sparkles,
} from 'lucide-react';

export const AskBackPanel = ({
  sessionId,
  field,
  onQuestionResolved,
  onClose,
}) => {
  // Pre-fill question based on section
  const getDefaultQuestion = (f) => {
    const sec = f?.section?.toLowerCase() || '';
    if (sec.includes('med')) {
      return `क्या आप यह दवाई (${f.content.slice(0, 40)}...) अभी भी नियमित रूप से ले रहे हैं? (Are you currently taking this medication daily?)`;
    }
    if (sec.includes('complaint') || sec.includes('hpi')) {
      return `क्या यह लक्षण पिछले 2-3 दिनों में अचानक बढ़ा है या धीरे-धीरे शुरू हुआ? (Did this symptom start suddenly or gradually?)`;
    }
    if (sec.includes('allergy')) {
      return `क्या इस दवाई या किसी अन्य चीज़ से कभी शरीर पर लाल चकत्ते या सांस फूलने की समस्या हुई है? (Have you ever experienced hives or breathlessness?)`;
    }
    return `कृपया इस लक्षण के बारे में विस्तार से बताएं: ${f.content.slice(0, 50)}...`;
  };

  const [questionText, setQuestionText] = useState(() => getDefaultQuestion(field));
  const [patientAnswer, setPatientAnswer] = useState('');
  const [status, setStatus] = useState('idle'); // idle | sending | waiting | received
  const [error, setError] = useState(null);

  const handleSend = async () => {
    if (!questionText.trim()) return;
    setStatus('sending');
    setError(null);

    try {
      // Send question to backend ask-back endpoint
      const res = await fetch('/api/interview/ask-back', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          field_id: field.field_id,
          question_text: questionText,
          answer_text: patientAnswer.trim() || undefined,
        }),
      });

      if (!res.ok) {
        throw new Error(`Ask-back failed: ${res.statusText}`);
      }

      const updatedField = await res.json();
      setStatus('received');

      if (onQuestionResolved) {
        onQuestionResolved(updatedField, patientAnswer || 'Patient responded via Kiosk interface.');
      }
    } catch (err) {
      console.warn('[AskBackPanel] Error:', err);
      setError(err.message || 'Failed to send question to kiosk.');
      setStatus('idle');
    }
  };

  return (
    <div
      style={{
        marginTop: '12px',
        padding: '18px',
        borderRadius: '12px',
        background: '#EFF6FF',
        border: '1.5px solid #BFDBFE',
        boxShadow: '0 4px 12px rgba(37, 99, 235, 0.08)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#1E40AF', fontWeight: 800, fontSize: '14px' }}>
          <MessageSquare size={18} />
          <span>Ask Patient via Kiosk (1-Tap Clarification)</span>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748B' }}
        >
          <X size={16} />
        </button>
      </div>

      <p style={{ fontSize: '13px', color: '#1E3A8A', margin: '0 0 10px 0' }}>
        Send a real-time question directly to the patient's waiting room screen or enter their in-person clarification:
      </p>

      {/* Editable question */}
      <textarea
        value={questionText}
        onChange={(e) => setQuestionText(e.target.value)}
        disabled={status === 'sending' || status === 'received'}
        style={{
          width: '100%',
          minHeight: '68px',
          padding: '10px 12px',
          borderRadius: '8px',
          border: '1.5px solid #93C5FD',
          fontSize: '13px',
          color: '#0F172A',
          background: '#FFF',
          boxSizing: 'border-box',
          outline: 'none',
          marginBottom: '10px',
        }}
      />

      {/* Synchronous Answer Option (Doctor cabin direct entry) */}
      <div style={{ marginBottom: '12px' }}>
        <input
          type="text"
          value={patientAnswer}
          onChange={(e) => setPatientAnswer(e.target.value)}
          placeholder="Optional: Enter verbal reply if patient is present in cabin..."
          disabled={status === 'sending' || status === 'received'}
          style={{
            width: '100%',
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid #CBD5E1',
            fontSize: '13px',
            background: '#FFF',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {error && (
        <div style={{ fontSize: '12px', color: '#DC2626', marginBottom: '8px', fontWeight: 600 }}>
          {error}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px' }}>
        {status === 'received' ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: '#059669',
              fontSize: '13px',
              fontWeight: 700,
            }}
          >
            <CheckCircle2 size={16} />
            <span>Clarification Recorded & Summary Updated!</span>
          </div>
        ) : (
          <button
            onClick={handleSend}
            disabled={status === 'sending' || !questionText.trim()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              background: '#2563EB',
              color: '#FFF',
              border: 'none',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              opacity: status === 'sending' ? 0.7 : 1,
            }}
          >
            {status === 'sending' ? (
              <>
                <Loader2 size={14} className="spin" />
                <span>Sending to Kiosk...</span>
              </>
            ) : (
              <>
                <Send size={14} />
                <span>Send to Kiosk / Save Answer</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default AskBackPanel;
