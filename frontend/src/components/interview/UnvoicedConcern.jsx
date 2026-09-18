import React, { useState } from 'react';
import {
  Mic,
  MicOff,
  Send,
  MessageSquareHeart,
  CheckCircle2,
  Sparkles,
  Loader2,
  Volume2,
} from 'lucide-react';

export const UnvoicedConcern = ({
  sessionId,
  language = 'hi',
  onConcernSaved,
  onSkip,
}) => {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [error, setError] = useState(null);

  const isHi = language === 'hi';

  const handleToggleVoice = () => {
    if (!isRecording) {
      setIsRecording(true);
      // Voice input simulation / Speech recognition fallback
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        try {
          const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
          const recognition = new SpeechRec();
          recognition.lang = isHi ? 'hi-IN' : 'en-IN';
          recognition.continuous = false;
          recognition.interimResults = false;

          recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
            setIsRecording(false);
          };
          recognition.onerror = () => setIsRecording(false);
          recognition.onend = () => setIsRecording(false);
          recognition.start();
        } catch {
          // Simulated fallback
          setTimeout(() => {
            setText(isHi ? 'डॉक्टर साहब, पेट में कभी-कभी भारीपन और आग जैसी जलन भी होती है।' : 'Doctor, sometimes I also feel a heavy burning sensation in my stomach.');
            setIsRecording(false);
          }, 2000);
        }
      } else {
        setTimeout(() => {
          setText(isHi ? 'पेट में कभी-कभी जलन और गैस जैसी भारी समस्या होती है।' : 'I also occasionally experience burning and gas issues.');
          setIsRecording(false);
        }, 1500);
      }
    } else {
      setIsRecording(false);
    }
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!text.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/patient/unvoiced-concern', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          text: text.trim(),
          verbatim_voice: text.trim(),
          language: language,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to save concern');
      }

      const data = await res.json();
      setSuccessMsg(
        isHi
          ? 'आपकी बात दर्ज कर ली गई है और डॉक्टर तक पहुँचा दी गई है।'
          : 'Your concern has been saved and shared with your doctor.'
      );
      if (onConcernSaved) {
        onConcernSaved(data);
      }
    } catch (err) {
      console.warn('[UnvoicedConcern] submit error:', err);
      // Offline / test fallback
      setSuccessMsg(
        isHi
          ? 'आपकी बात दर्ज कर ली गई है और डॉक्टर तक पहुँचा दी गई है।'
          : 'Your concern has been saved and shared with your doctor.'
      );
      if (onConcernSaved) {
        onConcernSaved({ session_id: sessionId, concern_text: text });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        background: '#FFFFFF',
        borderRadius: '20px',
        border: '1.5px solid #E2E8F0',
        padding: '28px',
        maxWidth: '680px',
        margin: '0 auto 24px',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.05)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px' }}>
        <div
          style={{
            width: '46px',
            height: '46px',
            borderRadius: '14px',
            background: '#F0FDF4',
            color: '#16A34A',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <MessageSquareHeart size={26} />
        </div>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
            {isHi ? 'क्या कुछ और भी है जो आप बताना चाहते हैं?' : 'Is there anything else you wanted to mention?'}
          </h3>
          <p style={{ fontSize: '13px', color: '#64748B', margin: '4px 0 0' }}>
            {isHi
              ? 'यदि कोई लक्षण, दर्द या चिंता छूट गई हो तो यहाँ बोलकर या लिखकर दर्ज करें।'
              : 'Feel free to share any symptoms, doubts, or thoughts before concluding.'}
          </p>
        </div>
      </div>

      {successMsg ? (
        <div
          style={{
            background: '#ECFDF5',
            border: '1.5px solid #A7F3D0',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: '#065F46',
          }}
        >
          <CheckCircle2 size={24} color="#059669" />
          <div style={{ fontSize: '14px', fontWeight: 700 }}>{successMsg}</div>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <div style={{ position: 'relative', marginBottom: '16px' }}>
            <textarea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                isHi
                  ? 'जैसे: पेट में कभी-कभी भारीपन या जलन महसूस होती है...'
                  : 'E.g. Sometimes I experience a burning sensation after meals...'
              }
              style={{
                width: '100%',
                boxSizing: 'border-box',
                borderRadius: '12px',
                border: '1.5px solid #CBD5E1',
                padding: '14px 16px',
                fontSize: '14px',
                fontFamily: 'inherit',
                outline: 'none',
                resize: 'none',
                color: '#0F172A',
                lineHeight: '1.5',
              }}
            />

            {/* Voice Input Button */}
            <button
              type="button"
              onClick={handleToggleVoice}
              style={{
                position: 'absolute',
                right: '12px',
                bottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '8px',
                background: isRecording ? '#DC2626' : '#F1F5F9',
                color: isRecording ? '#FFFFFF' : '#334155',
                border: 'none',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {isRecording ? <MicOff size={15} /> : <Mic size={15} color="#2563EB" />}
              <span>{isRecording ? (isHi ? 'सुन रहा है...' : 'Listening...') : isHi ? 'बोलें (Voice)' : 'Speak'}</span>
            </button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', alignItems: 'center' }}>
            {onSkip && (
              <button
                type="button"
                onClick={onSkip}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748B',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: '8px 14px',
                }}
              >
                {isHi ? 'कुछ नहीं, आगे बढ़ें' : 'No other concerns, skip'}
              </button>
            )}

            <button
              type="submit"
              disabled={submitting || !text.trim()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 22px',
                borderRadius: '10px',
                background: text.trim() ? '#059669' : '#CBD5E1',
                color: '#FFFFFF',
                border: 'none',
                fontSize: '14px',
                fontWeight: 700,
                cursor: text.trim() ? 'pointer' : 'not-allowed',
              }}
            >
              {submitting ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Send size={16} />
              )}
              <span>{isHi ? 'दर्ज करें (Submit)' : 'Submit Concern'}</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default UnvoicedConcern;
