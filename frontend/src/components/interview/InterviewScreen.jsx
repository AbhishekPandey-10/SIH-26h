import React, { useState, useEffect, useRef } from 'react';

/**
 * MediKiosk InterviewScreen Component
 * PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
 *
 * Features:
 * - Real-time WebSocket connection to /ws/interview?session_id=dev-test-001
 * - Dual-mode input: Microphone (ASR) + Text input fallback + Quick-tap option chips
 * - ASR failure handling (prompts "Please type your answer" after 2x consecutive failures)
 * - TTS auto-reading (audio URL playback with Web Speech API fallback)
 * - Emergency Red-Flag detection alert banner
 * - Adaptive progress indicator
 */
export function InterviewScreen({ sessionId = "dev-test-001", language = "hi" }) {
  // Interview state
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [progressPct, setProgressPct] = useState(10);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [history, setHistory] = useState([]);
  
  // Input mode state
  const [inputText, setInputText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [asrFailures, setAsrFailures] = useState(0);
  const [asrStatusMessage, setAsrStatusMessage] = useState("");
  const [redFlagAlert, setRedFlagAlert] = useState(null);

  // WebSocket & Speech references
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const audioPlayerRef = useRef(null);
  const inputRef = useRef(null);

  // 1. Initialize WebSocket connection
  useEffect(() => {
    const wsUrl = (import.meta.env?.VITE_WS_BASE_URL || "ws://localhost:8000") + 
      `/ws/interview?session_id=${sessionId}`;
    
    setConnectionStatus("connecting");
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      console.log("[InterviewWS] Connected to", wsUrl);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Check if message is a separate red_flag_triggered event
        if (data.event === "red_flag_triggered") {
          console.warn("[InterviewWS] RED FLAG TRIGGERED:", data.data);
          setRedFlagAlert(data.data);
          return;
        }

        // Standard NextQuestion payload
        setCurrentQuestion(data);
        if (typeof data.progress_pct === "number") {
          setProgressPct(data.progress_pct);
        }

        // Check if question includes red flag warning
        if (data.is_red_flag_warning && data.red_flag_details) {
          setRedFlagAlert(data.red_flag_details);
        }

        // Auto-play TTS for the new question
        playTTS(data.text, data.audio_url, language);

      } catch (err) {
        console.error("[InterviewWS] Error parsing message:", err, event.data);
      }
    };

    ws.onerror = (err) => {
      console.error("[InterviewWS] Connection error:", err);
      setConnectionStatus("error");
    };

    ws.onclose = () => {
      console.log("[InterviewWS] Disconnected");
      setConnectionStatus("disconnected");
    };

    return () => {
      if (ws) ws.close();
    };
  }, [sessionId, language]);

  // 2. TTS Player (audio_url or Web Speech API fallback)
  const playTTS = (text, audioUrl, lang) => {
    if (audioUrl) {
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio(audioUrl);
      } else {
        audioPlayerRef.current.src = audioUrl;
      }
      audioPlayerRef.current.play().catch((e) => console.warn("Audio play error:", e));
      return;
    }

    // Web Speech API fallback
    if ('speechSynthesis' in window && text) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === "hi" ? "hi-IN" : "en-IN";
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  // 3. Send Answer to Engine
  const sendAnswer = (answerText, verbatimVoice = null) => {
    if (!answerText || !answerText.trim()) return;

    const trimmed = answerText.trim();

    // Record turn in history
    if (currentQuestion) {
      setHistory((prev) => [
        ...prev,
        { question: currentQuestion.text, answer: trimmed, verbatimVoice }
      ]);
    }

    const payload = {
      session_id: sessionId,
      answer: trimmed,
      verbatim_voice: verbatimVoice || trimmed,
      language: language,
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      setInputText("");
      setAsrStatusMessage("");
    } else {
      console.warn("WebSocket is not open. Unable to send answer.");
    }
  };

  // 4. Voice ASR with Web Speech API & Failure fallback
  const startRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setAsrStatusMessage("Browser voice recognition not supported. Please type your answer.");
      setAsrFailures((prev) => prev + 1);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setIsRecording(true);
      setAsrStatusMessage("सुन रहे हैं... कृपया बोलें (Listening...)");

      let receivedSpeech = false;

      recognition.onresult = (event) => {
        receivedSpeech = true;
        const transcript = event.results[0][0].transcript;
        const confidence = event.results[0][0].confidence;
        console.log("[ASR Result]", transcript, "Confidence:", confidence);

        if (transcript && transcript.trim()) {
          setAsrFailures(0);
          setIsRecording(false);
          setAsrStatusMessage("");
          sendAnswer(transcript, transcript);
        } else {
          handleAsrFailure("Empty speech input");
        }
      };

      recognition.onerror = (event) => {
        console.warn("[ASR Error]", event.error);
        setIsRecording(false);
        handleAsrFailure(event.error);
      };

      recognition.onend = () => {
        setIsRecording(false);
        if (!receivedSpeech) {
          handleAsrFailure("No speech detected");
        }
      };

      recognition.start();
    } catch (err) {
      console.error("Failed to start voice recognition:", err);
      setIsRecording(false);
      handleAsrFailure("Initialization failed");
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsRecording(false);
  };

  const handleAsrFailure = (reason) => {
    setAsrFailures((prev) => {
      const nextFailures = prev + 1;
      if (nextFailures >= 2) {
        setAsrStatusMessage("आवाज़ समझ नहीं आई। कृपया अपना उत्तर नीचे टाइप करें (Please type your answer)");
        if (inputRef.current) {
          inputRef.current.focus();
        }
      } else {
        setAsrStatusMessage("आवाज़ स्पष्ट नहीं थी, कृपया दोबारा बोलें या टाइप करें");
      }
      return nextFailures;
    });
  };

  return (
    <div style={styles.container}>
      {/* Header with Connection & Progress */}
      <div style={styles.header}>
        <div style={styles.titleRow}>
          <h2 style={styles.title}>MediKiosk AI OPD Intake</h2>
          <div style={styles.statusBadge(connectionStatus)}>
            {connectionStatus === "connected" ? "🟢 Live" : connectionStatus}
          </div>
        </div>

        {/* Progress Bar */}
        <div style={styles.progressBarTrack}>
          <div style={{ ...styles.progressBarFill, width: `${progressPct}%` }} />
        </div>
        <div style={styles.progressText}>
          <span>{currentQuestion ? currentQuestion.section.toUpperCase() : "INTAKE"}</span>
          <span>{progressPct.toFixed(0)}% Complete</span>
        </div>
      </div>

      {/* Emergency Red-Flag Banner */}
      {redFlagAlert && (
        <div style={styles.redFlagBanner}>
          <div style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
            ⚠️ आपातकालीन चेतावनी / Clinical Safety Alert: {redFlagAlert.category?.toUpperCase()}
          </div>
          <div style={{ marginTop: '4px', fontSize: '0.95rem' }}>
            लक्षण: "{redFlagAlert.trigger_phrase}" दर्ज किया गया है।
            कृपया शांत रहें, अस्पताल स्टाफ को सूचित कर दिया गया है।
          </div>
        </div>
      )}

      {/* Current Question Card */}
      <div style={styles.questionCard}>
        {currentQuestion ? (
          <>
            <div style={styles.questionText}>{currentQuestion.text}</div>
            
            {/* Quick-Tap Options */}
            {currentQuestion.options && currentQuestion.options.length > 0 && (
              <div style={styles.optionsContainer}>
                <div style={styles.optionsHeader}>त्वरित विकल्प (Quick Choices):</div>
                <div style={styles.chipGrid}>
                  {currentQuestion.options.map((opt, i) => (
                    <button
                      key={i}
                      style={styles.chipButton}
                      onClick={() => sendAnswer(opt)}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            सत्र शुरू हो रहा है... कृपया प्रतीक्षा करें (Initializing clinical intake session...)
          </div>
        )}
      </div>

      {/* ASR Notification Banner */}
      {asrStatusMessage && (
        <div style={styles.asrMessageBanner(asrFailures >= 2)}>
          {asrStatusMessage}
        </div>
      )}

      {/* Dual-Mode Input Panel */}
      <div style={styles.inputPanel}>
        {/* Voice Microphone Button */}
        <button
          style={styles.micButton(isRecording)}
          onClick={isRecording ? stopRecording : startRecording}
          title={isRecording ? "Stop Recording" : "Tap to Speak"}
        >
          {isRecording ? "⏹️ सुन रहे हैं..." : "🎙️ बोलकर उत्तर दें (Speak)"}
        </button>

        {/* Text Input Fallback */}
        <form
          style={styles.textForm}
          onSubmit={(e) => {
            e.preventDefault();
            sendAnswer(inputText);
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={asrFailures >= 2 ? "यहाँ टाइप करें (Please type your answer here)..." : "या यहाँ टाइप करें (Or type your answer)..."}
            style={styles.textInput(asrFailures >= 2)}
          />
          <button type="submit" style={styles.sendButton} disabled={!inputText.trim()}>
            भेजें (Send)
          </button>
        </form>
      </div>

      {/* Prior Turns Collapsible History */}
      {history.length > 0 && (
        <div style={styles.historySection}>
          <div style={styles.historyTitle}>पूर्व संवाद (Previous answers):</div>
          {history.slice(-3).map((item, idx) => (
            <div key={idx} style={styles.historyItem}>
              <div style={styles.historyQ}>डॉक्टर: {item.question}</div>
              <div style={styles.historyA}>रोगी: {item.answer}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '1.5rem',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    color: '#1f2937',
  },
  header: {
    marginBottom: '1.5rem',
    background: '#ffffff',
    padding: '1rem',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  titleRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
  },
  title: {
    margin: 0,
    fontSize: '1.4rem',
    fontWeight: '700',
    color: '#111827',
  },
  statusBadge: (status) => ({
    padding: '4px 10px',
    borderRadius: '16px',
    fontSize: '0.85rem',
    fontWeight: '600',
    background: status === 'connected' ? '#dcfce7' : '#fee2e2',
    color: status === 'connected' ? '#166534' : '#991b1b',
  }),
  progressBarTrack: {
    height: '10px',
    background: '#e5e7eb',
    borderRadius: '5px',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    background: '#2563eb',
    transition: 'width 0.4s ease-in-out',
  },
  progressText: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.8rem',
    color: '#6b7280',
    marginTop: '4px',
  },
  redFlagBanner: {
    background: '#fee2e2',
    border: '2px solid #ef4444',
    color: '#991b1b',
    padding: '1rem',
    borderRadius: '12px',
    marginBottom: '1.5rem',
    animation: 'pulse 2s infinite',
  },
  questionCard: {
    background: '#ffffff',
    borderRadius: '16px',
    padding: '2rem',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    marginBottom: '1.5rem',
    minHeight: '180px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  questionText: {
    fontSize: '1.4rem',
    lineHeight: '1.5',
    fontWeight: '600',
    color: '#1e3a8a',
    marginBottom: '1.5rem',
  },
  optionsContainer: {
    marginTop: '0.5rem',
  },
  optionsHeader: {
    fontSize: '0.9rem',
    fontWeight: '600',
    color: '#4b5563',
    marginBottom: '0.5rem',
  },
  chipGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
  },
  chipButton: {
    background: '#eff6ff',
    border: '1px solid #bfdbfe',
    color: '#1d4ed8',
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '0.95rem',
    cursor: 'pointer',
    fontWeight: '500',
    transition: 'all 0.15s ease',
  },
  asrMessageBanner: (isCritical) => ({
    background: isCritical ? '#fef3c7' : '#f3f4f6',
    border: `1px solid ${isCritical ? '#f59e0b' : '#d1d5db'}`,
    color: isCritical ? '#92400e' : '#374151',
    padding: '0.75rem',
    borderRadius: '8px',
    textAlign: 'center',
    marginBottom: '1rem',
    fontWeight: '500',
  }),
  inputPanel: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
    marginBottom: '1.5rem',
  },
  micButton: (isRecording) => ({
    background: isRecording ? '#dc2626' : '#2563eb',
    color: '#ffffff',
    border: 'none',
    padding: '1rem',
    borderRadius: '12px',
    fontSize: '1.1rem',
    fontWeight: 'bold',
    cursor: 'pointer',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
    transition: 'background 0.2s ease',
  }),
  textForm: {
    display: 'flex',
    gap: '0.5rem',
  },
  textInput: (isHighlighted) => ({
    flex: 1,
    padding: '0.75rem 1rem',
    borderRadius: '10px',
    border: isHighlighted ? '2px solid #f59e0b' : '1px solid #d1d5db',
    fontSize: '1rem',
    outline: 'none',
  }),
  sendButton: {
    background: '#10b981',
    color: '#ffffff',
    border: 'none',
    padding: '0.75rem 1.5rem',
    borderRadius: '10px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  historySection: {
    background: '#f9fafb',
    padding: '1rem',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
  },
  historyTitle: {
    fontWeight: '600',
    color: '#6b7280',
    fontSize: '0.85rem',
    marginBottom: '0.5rem',
  },
  historyItem: {
    marginBottom: '0.5rem',
    fontSize: '0.85rem',
  },
  historyQ: {
    color: '#4b5563',
  },
  historyA: {
    color: '#111827',
    fontWeight: '500',
  },
};

export default InterviewScreen;
