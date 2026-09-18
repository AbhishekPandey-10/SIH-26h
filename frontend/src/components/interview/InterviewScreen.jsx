import React, { useState, useEffect, useRef } from 'react';
import KioskCard from '../kiosk/KioskCard';
import KioskButton from '../kiosk/KioskButton';
import ProgressBar from '../kiosk/ProgressBar';
import {
  Mic,
  Square,
  Volume2,
  Send,
  CheckCircle2,
  AlertTriangle,
  Stethoscope,
  User,
  Activity,
  ArrowRight,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

const CLINICAL_FLOW_QUESTIONS_MAP = {
  en: [
    {
      section: 'Chief Complaint',
      text: 'What is your primary health concern today? Please describe your symptoms.',
      options: ['Severe Stomach Pain', 'Fever & Severe Headache', 'Chest Discomfort / Heaviness', 'Cough & Shortness of Breath'],
      progress_pct: 15,
    },
    {
      section: 'Onset & Duration',
      text: 'When did this issue begin and how long has it been persisting?',
      options: ['Since this morning', 'Past 2-3 days', 'More than 1 week', 'Chronic / Several months'],
      progress_pct: 35,
    },
    {
      section: 'Pain Severity',
      text: 'How severe is your pain or discomfort? Please select the severity level.',
      options: ['Mild (Score 1-3)', 'Moderate (Score 4-6)', 'Severe (Score 7-10)', 'Constantly worsening'],
      progress_pct: 55,
    },
    {
      section: 'Associated Symptoms',
      text: 'Do you also have nausea, dizziness, cold sweats, or other symptoms?',
      options: ['Yes, Nausea & Dizziness', 'Cold Sweats & Palpitations', 'Loose motions / Cramps', 'No other symptoms'],
      progress_pct: 75,
    },
    {
      section: 'Medical History',
      text: 'Do you take any regular medications or have diagnosed BP/Diabetes?',
      options: ['Diabetes / High Blood Sugar', 'High Blood Pressure (Hypertension)', 'Heart Condition', 'No prior conditions / Healthy'],
      progress_pct: 95,
    },
  ],
  hi: [
    {
      section: 'Chief Complaint',
      text: 'आपको मुख्य रूप से क्या परेशानी है? कृपया अपनी तकलीफ बताएं। (What brings you to the OPD today?)',
      options: ['पेट में तेज दर्द (Stomach Pain)', 'बुखार एवं सिरदर्द (Fever & Headache)', 'छाती में भारीपन (Chest Discomfort)', 'खांसी एवं सांस फूलना (Cough & Breathlessness)'],
      progress_pct: 15,
    },
    {
      section: 'Onset & Duration',
      text: 'यह तकलीफ कब से शुरू हुई और कितने समय से बनी हुई है? (How long have you had this issue?)',
      options: ['आज सुबह से (Since this morning)', 'पिछले 2-3 दिनों से (Past 2-3 days)', '1 सप्ताह से अधिक (Over 1 week)', 'महीनों से रुक-रुक कर (Chronic / Intermittent)'],
      progress_pct: 35,
    },
    {
      section: 'Pain Severity',
      text: 'दर्द अथवा तकलीफ कितनी गंभीर है? कृपया तीव्रता का चयन करें। (Rate your pain / severity)',
      options: ['हल्की तकलीफ (Mild 1-3)', 'मध्यम दर्द (Moderate 4-6)', 'असहनीय तेज दर्द (Severe 7-10)', 'लगातार बढ़ता हुआ (Worsening)'],
      progress_pct: 55,
    },
    {
      section: 'Associated Symptoms',
      text: 'क्या इसके साथ उल्टी, चक्कर, घबराहट या कोई अन्य लक्षण भी हैं? (Any associated nausea, dizziness, or sweating?)',
      options: ['हाँ, उल्टी व चक्कर (Nausea & Dizziness)', 'पसीना व घबराहट (Sweating & Palpitations)', 'दस्त या पेट मरोड़ (Loose motions)', 'कोई अन्य लक्षण नहीं (No other symptoms)'],
      progress_pct: 75,
    },
    {
      section: 'Medical History',
      text: 'क्या आप पहले से कोई नियमित दवाई ले रहे हैं या बीपी/शुगर की बीमारी है? (Pre-existing conditions or medications?)',
      options: ['डायबिटीज / शुगर (Diabetes)', 'हाई ब्लड प्रेशर (Hypertension)', 'हृदय रोग (Heart Condition)', 'कोई पुरानी बीमारी नहीं (None / Healthy)'],
      progress_pct: 95,
    },
  ],
  pa: [
    {
      section: 'Chief Complaint',
      text: 'ਤੁਹਾਨੂੰ ਮੁੱਖ ਤੌਰ ਤੇ ਕੀ ਤਕਲੀਫ਼ ਹੈ? ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਲੱਛਣ ਦੱਸੋ।',
      options: ['ਪੇਟ ਵਿੱਚ ਤੇਜ਼ ਦਰਦ', 'ਬੁਖਾਰ ਅਤੇ ਸਿਰਦਰਦ', 'ਛਾਤੀ ਵਿੱਚ ਭਾਰਾਪਨ', 'ਖੰਘ ਅਤੇ ਸਾਹ ਚੜ੍ਹਨਾ'],
      progress_pct: 15,
    },
    {
      section: 'Onset & Duration',
      text: 'ਇਹ ਤਕਲੀਫ਼ ਕਦੋਂ ਸ਼ੁਰੂ ਹੋਈ ਅਤੇ ਕਿੰਨੇ ਸਮੇਂ ਤੋਂ ਬਣੀ ਹੋਈ ਹੈ?',
      options: ['ਅੱਜ ਸਵੇਰ ਤੋਂ', 'ਪਿਛਲੇ 2-3 ਦਿਨਾਂ ਤੋਂ', '1 ਹਫ਼ਤੇ ਤੋਂ ਵੱਧ', 'ਕਈ ਮਹੀਨਿਆਂ ਤੋਂ'],
      progress_pct: 35,
    },
    {
      section: 'Pain Severity',
      text: 'ਦਰਦ ਜਾਂ ਤਕਲੀਫ਼ ਕਿੰਨੀ ਗੰਭੀਰ ਹੈ? ਤੀਬਰਤਾ ਚੁਣੋ।',
      options: ['ਹਲਕੀ ਤਕਲੀਫ਼ (1-3)', 'ਦਰਮਿਆਨਾ ਦਰਦ (4-6)', 'ਅਸਹਿਣਯੋਗ ਤੇਜ਼ ਦਰਦ (7-10)', 'ਲਗਾਤਾਰ ਵਧਦਾ ਹੋਇਆ'],
      progress_pct: 55,
    },
    {
      section: 'Associated Symptoms',
      text: 'ਕੀ ਇਸਦੇ ਨਾਲ ਉਲਟੀ, ਚੱਕਰ ਜਾਂ ਘਬਰਾਹਟ ਵੀ ਹੈ?',
      options: ['ਹਾਂ, ਉਲਟੀ ਅਤੇ ਚੱਕਰ', 'ਪਸੀਨਾ ਅਤੇ ਘਬਰਾਹਟ', 'ਦਸਤ ਜਾਂ ਪੇਟ ਮਰੋੜ', 'ਕੋਈ ਹੋਰ ਲੱਛਣ ਨਹੀਂ'],
      progress_pct: 75,
    },
    {
      section: 'Medical History',
      text: 'ਕੀ ਤੁਸੀਂ ਪਹਿਲਾਂ ਤੋਂ ਕੋਈ ਨਿਯਮਤ ਦਵਾਈ ਲੈ ਰਹੇ ਹੋ ਜਾਂ ਬੀਪੀ/ਸ਼ੂਗਰ ਹੈ?',
      options: ['ਸ਼ੂਗਰ (Diabetes)', 'ਹਾਈ ਬਲੱਡ ਪ੍ਰੈਸ਼ਰ (BP)', 'ਦਿਲ ਦੀ ਬਿਮਾਰੀ', 'ਕੋਈ ਪੁਰਾਣੀ ਬਿਮਾਰੀ ਨਹੀਂ'],
      progress_pct: 95,
    },
  ],
};

const INTERVIEW_UI_TEXT = {
  en: {
    title: 'AI OPD Clinical Intake',
    session: 'Session:',
    langLabel: 'Language:',
    liveStatus: 'Live AI Active',
    activeStatus: 'Smart Kiosk Active',
    stepPrefix: 'Section:',
    docQuestion: "Doctor's Question",
    listenAgain: 'Listen Again',
    quickOptions: 'Touch to select your answer:',
    tapToSpeak: 'Tap to Speak (Voice Answer)',
    tapToSpeakSub: 'Speak your symptoms in your own voice',
    listening: 'Listening... Tap to stop speaking',
    listeningSub: 'Tap when finished speaking',
    typePlaceholder: 'Or type your answer here...',
    typePrompt: 'Please type your answer here...',
    sendBtn: 'Send',
    sendSub: 'Send answer',
    completedTitle: 'Interview Successfully Completed!',
    completedDesc: 'Your symptoms and medical history have been compiled and sent to the OPD doctor.',
    summaryTitle: '📋 Clinical History Recorded:',
    collectSlipBtn: 'Collect OPD Slip & Finish',
    collectSlipSub: 'Finish session and take token',
    prevTurns: 'Previous Consultation Turns:',
    doctorLabel: 'Doctor',
    patientLabel: 'Patient',
  },
  hi: {
    title: 'कियोस्क क्लिनिकल साक्षात्कार (AI OPD Clinical Intake)',
    session: 'सत्र:',
    langLabel: 'भाषा:',
    liveStatus: 'लाइव AI सक्रिय (Live)',
    activeStatus: 'स्मार्ट कियोस्क मोड (Active)',
    stepPrefix: 'चरण:',
    docQuestion: "डॉक्टर का सवाल (Doctor's Question)",
    listenAgain: 'पुनः सुनें (Listen)',
    quickOptions: 'त्वरित विकल्प (Touch to select your answer):',
    tapToSpeak: 'बोलकर उत्तर दें (Tap to Speak)',
    tapToSpeakSub: 'अपनी आवाज में बीमारी या लक्षण बताएं',
    listening: 'सुन रहे हैं... बोलना समाप्त करने हेतु छुएं',
    listeningSub: 'Listening... Tap to stop speaking',
    typePlaceholder: 'अथवा यहाँ लिखकर भेजें (Or type your answer)...',
    typePrompt: 'यहाँ अपना उत्तर टाइप करें (Please type answer here)...',
    sendBtn: 'भेजें (Send)',
    sendSub: 'Send answer',
    completedTitle: 'साक्षात्कार सफलतापूर्वक पूर्ण हुआ!',
    completedDesc: 'आपकी सभी स्वास्थ्य जानकारियां, लक्षण और दवाइयों का विवरण ओपीडी डॉक्टर के कंप्यूटर पर भेज दिया गया है।',
    summaryTitle: '📋 डॉक्टर सारांश (Clinical History Recorded):',
    collectSlipBtn: 'पूर्ण करें एवं टोकन लें (Collect OPD Slip)',
    collectSlipSub: 'Finish session',
    prevTurns: 'पूर्व संवाद इतिहास (Previous Consultation Turns):',
    doctorLabel: 'डॉक्टर',
    patientLabel: 'रोगी',
  },
  pa: {
    title: 'ਕਿਓਸਕ ਕਲੀਨਿਕਲ ਇੰਟਰਵਿਊ (AI OPD Clinical Intake)',
    session: 'ਸੈਸ਼ਨ:',
    langLabel: 'ਭਾਸ਼ਾ:',
    liveStatus: 'ਲਾਈਵ AI ਸਰਗਰਮ',
    activeStatus: 'ਸਮਾਰਟ ਕਿਓਸਕ ਮੋਡ',
    stepPrefix: 'ਕਦਮ:',
    docQuestion: "ਡਾਕਟਰ ਦਾ ਸਵਾਲ (Doctor's Question)",
    listenAgain: 'ਦੁਬਾਰਾ ਸੁਣੋ (Listen)',
    quickOptions: 'ਤੇਜ਼ ਵਿਕਲਪ (ਆਪਣਾ ਉੱਤਰ ਚੁਣੋ):',
    tapToSpeak: 'ਬੋਲ ਕੇ ਉੱਤਰ ਦਿਓ (Tap to Speak)',
    tapToSpeakSub: 'ਆਪਣੀ ਆਵਾਜ਼ ਵਿੱਚ ਲੱਛਣ ਦੱਸੋ',
    listening: 'ਸੁਣ ਰਹੇ ਹਾਂ... ਬੋਲਣਾ ਸਮਾਪਤ ਕਰਨ ਲਈ ਛੂਹੋ',
    listeningSub: 'Listening... Tap to stop speaking',
    typePlaceholder: 'ਜਾਂ ਇੱਥੇ ਲਿਖ ਕੇ ਭੇਜੋ...',
    typePrompt: 'ਇੱਥੇ ਆਪਣਾ ਉੱਤਰ ਟਾਈਪ ਕਰੋ...',
    sendBtn: 'ਭੇਜੋ (Send)',
    sendSub: 'Send answer',
    completedTitle: 'ਇੰਟਰਵਿਊ ਸਫਲਤਾਪੂਰਵਕ ਸੰਪੂਰਨ ਹੋਈ!',
    completedDesc: 'ਤੁਹਾਡੇ ਸਾਰੇ ਲੱਛਣ ਅਤੇ ਜਾਣਕਾਰੀ ਓਪੀਡੀ ਡਾਕਟਰ ਦੇ ਕੰਪਿਊਟਰ ਤੇ ਭੇਜ ਦਿੱਤੀ ਗਈ ਹੈ।',
    summaryTitle: '📋 ਦਰਜ ਕਲੀਨਿਕਲ ਇਤਿਹਾਸ (Clinical History):',
    collectSlipBtn: 'ਪਰਚੀ ਲਓ ਅਤੇ ਸਮਾਪਤ ਕਰੋ (Collect Slip)',
    collectSlipSub: 'Finish session',
    prevTurns: 'ਪਿਛਲੀ ਗੱਲਬਾਤ ਦਾ ਇਤਿਹਾਸ:',
    doctorLabel: 'ਡਾਕਟਰ',
    patientLabel: 'ਮਰੀਜ਼',
  },
};

export function InterviewScreen({ sessionId = 'dev-test-001', language = 'hi', onFinish = null }) {
  const currentLang = language || 'hi';
  const questionsList = CLINICAL_FLOW_QUESTIONS_MAP[currentLang] || CLINICAL_FLOW_QUESTIONS_MAP.hi;
  const t = INTERVIEW_UI_TEXT[currentLang] || INTERVIEW_UI_TEXT.hi;

  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState(questionsList[0]);
  const [progressPct, setProgressPct] = useState(15);
  const [connectionStatus, setConnectionStatus] = useState('connected');
  const [history, setHistory] = useState([]);
  const [isCompleted, setIsCompleted] = useState(false);

  // Input states
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [asrFailures, setAsrFailures] = useState(0);
  const [asrStatusMessage, setAsrStatusMessage] = useState('');
  const [redFlagAlert, setRedFlagAlert] = useState(null);

  // References
  const wsRef = useRef(null);
  const recognitionRef = useRef(null);
  const audioPlayerRef = useRef(null);
  const inputRef = useRef(null);

  // Synchronize current question if language changes
  useEffect(() => {
    const list = CLINICAL_FLOW_QUESTIONS_MAP[currentLang] || CLINICAL_FLOW_QUESTIONS_MAP.hi;
    if (list[currentQuestionIndex]) {
      setCurrentQuestion(list[currentQuestionIndex]);
    }
  }, [currentLang, currentQuestionIndex]);

  // 1. Initialize WebSocket with Graceful Fallback
  useEffect(() => {
    const wsBase = import.meta.env?.VITE_WS_BASE_URL || 'http://localhost:8000'.replace('http', 'ws');
    const wsUrl = `${wsBase}/ws/interview?session_id=${sessionId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('connected');
        console.log('[InterviewWS] Connected to live backend at', wsUrl);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.event === 'red_flag_triggered') {
            setRedFlagAlert(data.data);
            return;
          }

          setCurrentQuestion(data);
          if (typeof data.progress_pct === 'number') {
            setProgressPct(data.progress_pct);
          }
          if (data.is_red_flag_warning && data.red_flag_details) {
            setRedFlagAlert(data.red_flag_details);
          }

          playTTS(data.text, data.audio_url, currentLang);
        } catch (err) {
          console.warn('[InterviewWS] Message parse notice:', err);
        }
      };

      ws.onerror = () => {
        setConnectionStatus('offline-sandbox');
      };

      ws.onclose = () => {
        setConnectionStatus('offline-sandbox');
      };

      return () => {
        if (ws) ws.close();
      };
    } catch (e) {
      setConnectionStatus('offline-sandbox');
    }
  }, [sessionId, currentLang]);

  // Read initial question aloud on mount / change
  useEffect(() => {
    if (currentQuestion && currentQuestion.text) {
      playTTS(currentQuestion.text, null, currentLang);
    }
  }, [currentQuestionIndex, currentQuestion?.text]);

  // 2. TTS Voice Playback
  const playTTS = (text, audioUrl, lang) => {
    if (audioUrl) {
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio(audioUrl);
      } else {
        audioPlayerRef.current.src = audioUrl;
      }
      audioPlayerRef.current.play().catch(() => {});
      return;
    }

    if ('speechSynthesis' in window && text) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === 'hi' ? 'hi-IN' : lang === 'pa' ? 'pa-IN' : 'en-IN';
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  // 3. Send Answer (via WebSocket or Local Simulation)
  const sendAnswer = (answerText, verbatimVoice = null) => {
    if (!answerText || !answerText.trim()) return;
    const trimmed = answerText.trim();

    // Check emergency red flags
    const lower = trimmed.toLowerCase();
    if (
      lower.includes('छाती में तेज') ||
      lower.includes('heart attack') ||
      lower.includes('chest pain') ||
      lower.includes('बेहोश') ||
      lower.includes('blood in vomit')
    ) {
      setRedFlagAlert({
        category: 'CARDIOVASCULAR EMERGENCY',
        trigger_phrase: trimmed,
        priority: 'IMMEDIATE OPD TRIAGE',
      });
    }

    // Add to turn history
    const questionText = currentQuestion ? currentQuestion.text : 'Question';
    setHistory((prev) => [
      ...prev,
      {
        question: questionText,
        answer: trimmed,
        section: currentQuestion?.section || 'Intake',
      },
    ]);

    // Send to WebSocket if live
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          session_id: sessionId,
          answer: trimmed,
          verbatim_voice: verbatimVoice || trimmed,
          language: currentLang,
        })
      );
    } else {
      // Local fallback simulation step
      const nextIdx = currentQuestionIndex + 1;
      if (nextIdx < questionsList.length) {
        setCurrentQuestionIndex(nextIdx);
        setCurrentQuestion(questionsList[nextIdx]);
        setProgressPct(questionsList[nextIdx].progress_pct);
      } else {
        setIsCompleted(true);
        setProgressPct(100);
      }
    }

    setInputText('');
    setAsrStatusMessage('');
  };

  // 4. Voice Speech Recognition
  const startRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setAsrStatusMessage(
        currentLang === 'en'
          ? 'Voice recognition not supported on this browser. Please type or tap an option below.'
          : 'ब्राउज़र में आवाज़ पहचान उपलब्ध नहीं है। कृपया नीचे टाइप करें या विकल्प चुनें।'
      );
      setAsrFailures((prev) => prev + 1);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.lang = currentLang === 'hi' ? 'hi-IN' : currentLang === 'pa' ? 'pa-IN' : 'en-IN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setIsRecording(true);
      setAsrStatusMessage(
        currentLang === 'en'
          ? '🎙️ Listening... Please describe your symptoms now.'
          : '🎙️ सुन रहे हैं... कृपया अपनी तकलीफ बोलें (Listening...)'
      );

      let receivedSpeech = false;

      recognition.onresult = (event) => {
        receivedSpeech = true;
        const transcript = event.results[0][0].transcript;
        if (transcript && transcript.trim()) {
          setAsrFailures(0);
          setIsRecording(false);
          setAsrStatusMessage('');
          sendAnswer(transcript, transcript);
        } else {
          handleAsrFailure('Empty speech');
        }
      };

      recognition.onerror = (event) => {
        setIsRecording(false);
        handleAsrFailure(event.error);
      };

      recognition.onend = () => {
        setIsRecording(false);
        if (!receivedSpeech) {
          handleAsrFailure('No speech detected');
        }
      };

      recognition.start();
    } catch (err) {
      setIsRecording(false);
      handleAsrFailure('Initialization error');
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

  const handleAsrFailure = () => {
    setAsrFailures((prev) => {
      const nextFailures = prev + 1;
      if (nextFailures >= 2) {
        setAsrStatusMessage(
          currentLang === 'en'
            ? 'Could not hear clearly. Please tap one of the quick options below or type your answer.'
            : 'आवाज़ स्पष्ट नहीं आई। कृपया नीचे दिए गए विकल्पों में से एक चुनें अथवा टाइप करें।'
        );
        if (inputRef.current) inputRef.current.focus();
      } else {
        setAsrStatusMessage(
          currentLang === 'en'
            ? 'Voice was not clear. Please speak again or select an option.'
            : 'आवाज़ स्पष्ट नहीं थी, कृपया दोबारा बोलें अथवा विकल्प चुनें।'
        );
      }
      return nextFailures;
    });
  };

  const handleFinish = () => {
    if (onFinish) {
      onFinish();
    } else {
      window.location.reload();
    }
  };

  return (
    <div
      style={{
        maxWidth: '920px',
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* Header with OPD Progress & Connection */}
      <div
        style={{
          background: '#FFFFFF',
          padding: '20px 24px',
          borderRadius: '16px',
          border: '2px solid #E2E8F0',
          boxShadow: '0 4px 14px rgba(15, 23, 42, 0.05)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: '#ECFDF5',
                color: '#059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Stethoscope size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                {t.title}
              </h2>
              <span style={{ fontSize: '13px', color: '#64748B' }}>
                {t.session} {sessionId} · {t.langLabel} {currentLang.toUpperCase()}
              </span>
            </div>
          </div>

          <div
            style={{
              padding: '6px 14px',
              borderRadius: '999px',
              fontSize: '13px',
              fontWeight: 800,
              background: connectionStatus === 'connected' ? '#ECFDF5' : '#F0F9FF',
              color: connectionStatus === 'connected' ? '#065F46' : '#0284C7',
              border: `1.5px solid ${connectionStatus === 'connected' ? '#A7F3D0' : '#BAE6FD'}`,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: connectionStatus === 'connected' ? '#059669' : '#0284C7',
              }}
            />
            <span>{connectionStatus === 'connected' ? t.liveStatus : t.activeStatus}</span>
          </div>
        </div>

        {/* Progress Bar */}
        <ProgressBar
          progress={progressPct}
          label={`${t.stepPrefix} ${currentQuestion?.section || 'Intake'}`}
          color="green"
        />
      </div>

      {/* Emergency Red-Flag Banner */}
      {redFlagAlert && (
        <div
          style={{
            background: '#FEF2F2',
            border: '2.5px solid #EF4444',
            color: '#991B1B',
            padding: '20px 24px',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '16px',
            boxShadow: '0 4px 16px rgba(220, 38, 38, 0.15)',
          }}
        >
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              background: '#DC2626',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <AlertTriangle size={26} />
          </div>

          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, margin: '0 0 4px 0' }}>
              ⚠️ Emergency Alert: {redFlagAlert.category}
            </h3>
            <p style={{ fontSize: '15px', margin: 0, lineHeight: 1.4 }}>
              Critical symptom reported: <strong>"{redFlagAlert.trigger_phrase}"</strong>.
              Priority alert sent to OPD nursing staff and triage doctor. Please remain calm.
            </p>
          </div>
        </div>
      )}

      {/* When Completed */}
      {isCompleted ? (
        <KioskCard
          padding="40px"
          highlight="green"
          style={{ textAlign: 'center', background: '#FFFFFF' }}
        >
          <div
            style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              background: '#ECFDF5',
              color: '#059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              border: '3px solid #A7F3D0',
            }}
          >
            <CheckCircle2 size={46} />
          </div>

          <h2 style={{ fontSize: '30px', fontWeight: 800, color: '#0F172A', marginBottom: '8px' }}>
            {t.completedTitle}
          </h2>
          <p style={{ fontSize: '18px', color: '#475569', maxWidth: '600px', margin: '0 auto 28px' }}>
            {t.completedDesc}
          </p>

          <div
            style={{
              background: '#F8FAFC',
              borderRadius: '14px',
              border: '1.5px solid #E2E8F0',
              padding: '20px',
              maxWidth: '640px',
              margin: '0 auto 28px',
              textAlign: 'left',
            }}
          >
            <h4 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginBottom: '12px' }}>
              {t.summaryTitle}
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {history.map((item, idx) => (
                <div key={idx} style={{ fontSize: '15px' }}>
                  <strong style={{ color: '#0284C7' }}>{item.section}:</strong>{' '}
                  <span style={{ color: '#0F172A', fontWeight: 600 }}>{item.answer}</span>
                </div>
              ))}
            </div>
          </div>

          <KioskButton
            variant="primary"
            size="xl"
            icon={<CheckCircle2 size={24} />}
            onClick={handleFinish}
            sublabel={t.collectSlipSub}
          >
            {t.collectSlipBtn}
          </KioskButton>
        </KioskCard>
      ) : (
        <>
          {/* Active Question Card */}
          <KioskCard
            padding="36px"
            style={{
              background: '#FFFFFF',
              border: '2.5px solid #E2E8F0',
              boxShadow: '0 8px 24px rgba(15, 23, 42, 0.06)',
            }}
          >
            {/* Top Question Tag & Audio Replay Button */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '16px',
              }}
            >
              <span
                style={{
                  fontSize: '13px',
                  fontWeight: 800,
                  color: '#059669',
                  background: '#ECFDF5',
                  padding: '4px 12px',
                  borderRadius: '999px',
                  border: '1px solid #A7F3D0',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                {t.docQuestion}
              </span>

              <button
                type="button"
                onClick={() => playTTS(currentQuestion?.text, currentQuestion?.audio_url, currentLang)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: '10px',
                  background: '#F0F9FF',
                  border: '1.5px solid #BAE6FD',
                  color: '#0284C7',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
                title="Hear question again"
              >
                <Volume2 size={18} />
                <span>{t.listenAgain}</span>
              </button>
            </div>

            {/* Question Heading */}
            <div
              style={{
                fontSize: '24px',
                fontWeight: 800,
                color: '#0F172A',
                lineHeight: 1.4,
                marginBottom: '28px',
              }}
            >
              {currentQuestion?.text}
            </div>

            {/* Quick-Tap Options (Large high-contrast touch chips) */}
            {currentQuestion?.options && currentQuestion.options.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: '15px',
                    fontWeight: 700,
                    color: '#64748B',
                    marginBottom: '12px',
                  }}
                >
                  {t.quickOptions}
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: '12px',
                  }}
                >
                  {currentQuestion.options.map((opt, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => sendAnswer(opt)}
                      style={{
                        padding: '16px 18px',
                        borderRadius: '14px',
                        background: '#FFFFFF',
                        border: '2px solid #CBD5E1',
                        color: '#0F172A',
                        fontSize: '17px',
                        fontWeight: 700,
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        boxShadow: '0 2px 4px rgba(15, 23, 42, 0.04)',
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#059669';
                        e.currentTarget.style.background = '#F0FDF4';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#CBD5E1';
                        e.currentTarget.style.background = '#FFFFFF';
                      }}
                    >
                      <span>{opt}</span>
                      <ArrowRight size={18} color="#059669" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </KioskCard>

          {/* ASR Status Message Banner */}
          {asrStatusMessage && (
            <div
              style={{
                background: asrFailures >= 2 ? '#FFFBEB' : '#F0F9FF',
                border: `2px solid ${asrFailures >= 2 ? '#F59E0B' : '#BAE6FD'}`,
                color: asrFailures >= 2 ? '#92400E' : '#0369A1',
                padding: '14px 20px',
                borderRadius: '14px',
                fontSize: '16px',
                fontWeight: 700,
                textAlign: 'center',
              }}
            >
              {asrStatusMessage}
            </div>
          )}

          {/* Voice Input Hero Area & Fallback Text Box */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            {/* Giant Microphone Button */}
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              style={{
                width: '100%',
                padding: '24px 32px',
                borderRadius: '18px',
                border: isRecording ? '3px solid #DC2626' : '3px solid #047857',
                background: isRecording ? '#DC2626' : '#059669',
                color: '#FFFFFF',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '16px',
                boxShadow: isRecording
                  ? '0 0 0 8px rgba(220, 38, 38, 0.25)'
                  : '0 8px 24px rgba(5, 150, 105, 0.3)',
                transition: 'all 0.2s ease',
              }}
            >
              {isRecording ? (
                <>
                  <Square size={32} fill="#FFFFFF" />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800 }}>{t.listening}</div>
                    <div style={{ fontSize: '15px', opacity: 0.9 }}>{t.listeningSub}</div>
                  </div>
                </>
              ) : (
                <>
                  <Mic size={36} />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800 }}>{t.tapToSpeak}</div>
                    <div style={{ fontSize: '15px', opacity: 0.9 }}>{t.tapToSpeakSub}</div>
                  </div>
                </>
              )}
            </button>

            {/* Text Input Fallback Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendAnswer(inputText);
              }}
              style={{
                display: 'flex',
                gap: '12px',
              }}
            >
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={asrFailures >= 2 ? t.typePrompt : t.typePlaceholder}
                style={{
                  flex: 1,
                  padding: '18px 22px',
                  borderRadius: '14px',
                  border: '2px solid #CBD5E1',
                  background: '#FFFFFF',
                  color: '#0F172A',
                  fontSize: '18px',
                  outline: 'none',
                }}
              />

              <KioskButton
                type="submit"
                variant="primary"
                size="lg"
                icon={<Send size={22} />}
                disabled={!inputText.trim()}
                onClick={() => sendAnswer(inputText)}
                sublabel={t.sendSub}
              >
                {t.sendBtn}
              </KioskButton>
            </form>
          </div>

          {/* Turn History Transcript */}
          {history.length > 0 && (
            <div
              style={{
                background: '#FFFFFF',
                borderRadius: '16px',
                border: '1.5px solid #E2E8F0',
                padding: '24px',
                boxShadow: '0 2px 8px rgba(15, 23, 42, 0.04)',
              }}
            >
              <h4 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginBottom: '16px' }}>
                {t.prevTurns}
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {history.slice(-4).map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      padding: '14px',
                      borderRadius: '12px',
                      background: '#F8FAFC',
                      border: '1px solid #E2E8F0',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#0284C7', fontWeight: 700, fontSize: '14px' }}>
                      <Stethoscope size={16} />
                      <span>{t.doctorLabel} ({item.section}): {item.question}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#0F172A', fontWeight: 800, fontSize: '16px', paddingLeft: '24px' }}>
                      <User size={16} color="#059669" />
                      <span>{t.patientLabel}: "{item.answer}"</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default InterviewScreen;
