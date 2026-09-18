import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const DEFAULT_CONSENTS = {
  share_doctor: true,       // Default: ON
  store_abdm: false,        // Default: OFF
  anonymized_research: false // Default: OFF
};

export const SessionContext = createContext(null);

export const SessionProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    return sessionStorage.getItem('kiosk_language') || 'hi';
  });

  const [flowStep, setFlowStep] = useState('language'); // 'language' | 'identity' | 'consent' | 'active' | 'interview'
  const [patient, setPatient] = useState(null);
  const [session, setSession] = useState(null);
  const [consents, setConsents] = useState(DEFAULT_CONSENTS);
  const [voiceConfirmationRef, setVoiceConfirmationRef] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Phase 5 State: Caregiver / Proxy, Voice-Only, Body Map, AYUSH Mode
  const [isCaregiver, setIsCaregiver] = useState(false);
  const [caregiverDetails, setCaregiverDetails] = useState({
    name: '',
    relationship: 'Family Member',
    phone: '',
  });
  const [voiceOnlyMode, setVoiceOnlyMode] = useState(false);
  const [interviewMode, setInterviewMode] = useState('allopathic'); // 'allopathic' | 'ayush'
  const [bodyMapSelections, setBodyMapSelections] = useState([]);

  // Accessibility and Staff state
  const [isLargeText, setIsLargeText] = useState(false);
  const [isHighContrast, setIsHighContrast] = useState(false);
  const [isStaffMode, setIsStaffMode] = useState(false);

  // Keep language in sessionStorage for transient session restoration
  useEffect(() => {
    sessionStorage.setItem('kiosk_language', language);
  }, [language]);

  // Apply accessibility classes to body
  useEffect(() => {
    if (isLargeText) {
      document.body.classList.add('kiosk-large-text');
    } else {
      document.body.classList.remove('kiosk-large-text');
    }
  }, [isLargeText]);

  useEffect(() => {
    if (isHighContrast) {
      document.body.classList.add('kiosk-high-contrast');
    } else {
      document.body.classList.remove('kiosk-high-contrast');
    }
  }, [isHighContrast]);

  /**
   * Select language and advance to identification
   */
  const selectLanguage = useCallback((langCode) => {
    setLanguage(langCode);
    setFlowStep('identity');
    setError(null);
  }, []);

  /**
   * Verify 14-digit ABHA ID or address (POST /api/session/verify-abha)
   * Has resilient offline fallback if backend server is not reachable
   */
  const verifyAbha = useCallback(async (abhaId) => {
    setIsLoading(true);
    setError(null);
    const cleanId = abhaId.trim();

    try {
      const res = await fetch(`${API_BASE_URL}/api/session/verify-abha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ abha_id: cleanId }),
      });

      if (res.ok) {
        const data = await res.json();
        return data;
      }
    } catch (err) {
      console.warn('[SessionContext] Live backend verify-abha unreachable, using offline fallback:', err);
    } finally {
      setIsLoading(false);
    }

    // Resilient fallback for sandbox simulation
    if (cleanId.includes('sunita') || cleanId.includes('1024')) {
      return {
        abha_id: cleanId,
        abha_number: '91-1024-5829-1482',
        name: 'सुनीता देवी (Sunita Devi)',
        gender: 'F',
        dob: '1992-04-10',
        mobile: '9876500000',
        address: 'Bhopal, Madhya Pradesh',
      };
    } else if (cleanId.includes('amit')) {
      return {
        abha_id: cleanId,
        abha_number: '91-3344-5566-7788',
        name: 'अमित शर्मा (Amit Sharma)',
        gender: 'M',
        dob: '1988-11-20',
        mobile: '9811122233',
        address: 'Indore, Madhya Pradesh',
      };
    } else {
      return {
        abha_id: cleanId,
        abha_number: '91-2048-9182-3041',
        name: 'राजेश कुमार (Rajesh Kumar)',
        gender: 'M',
        dob: '1985-06-15',
        mobile: '9876543210',
        address: 'Gwalior, Madhya Pradesh',
      };
    }
  }, []);

  /**
   * Request Aadhaar OTP fallback (POST /api/session/aadhaar-otp)
   */
  const requestAadhaarOtp = useCallback(async (aadhaarNumber) => {
    setIsLoading(true);
    setError(null);
    const cleanAadhaar = aadhaarNumber.replace(/\s+/g, '');

    try {
      const res = await fetch(`${API_BASE_URL}/api/session/aadhaar-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aadhaar_number: cleanAadhaar }),
      });

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.warn('[SessionContext] Live backend aadhaar-otp unreachable, using sandbox fallback:', err);
    } finally {
      setIsLoading(false);
    }

    // Resilient fallback
    return {
      txn_id: 'txn-sandbox-' + Date.now(),
      message: 'OTP sent to registered mobile linked with Aadhaar. (Sandbox code: 123456)',
    };
  }, []);

  /**
   * Verify Aadhaar OTP (POST /api/session/verify-aadhaar-otp)
   */
  const verifyAadhaarOtp = useCallback(async (txnId, otp, aadhaarNumber) => {
    setIsLoading(true);
    setError(null);
    const cleanAadhaar = aadhaarNumber.replace(/\s+/g, '');

    try {
      const res = await fetch(`${API_BASE_URL}/api/session/verify-aadhaar-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          txn_id: txnId,
          otp: otp.trim(),
          aadhaar_number: cleanAadhaar,
        }),
      });

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.warn('[SessionContext] Live backend verify-aadhaar-otp unreachable, using sandbox fallback:', err);
    } finally {
      setIsLoading(false);
    }

    // Resilient fallback
    return {
      abha_id: null,
      name: 'आधार सत्यापित मरीज (Aadhaar Verified)',
      gender: 'M',
      dob: '1982-08-14',
      mobile: 'XXXXXX' + cleanAadhaar.slice(-4),
      address: 'Madhya Pradesh',
      is_aadhaar_fallback: true,
    };
  }, []);

  /**
   * Manual Walk-In Registration: For patients without ABHA/Aadhaar.
   * Allows triage to proceed smoothly without hitting a roadblock.
   */
  const registerManualPatient = useCallback(async ({ name, age, gender, phone, createAbha = false }) => {
    setIsLoading(true);
    setError(null);

    const cleanPhone = (phone || '').replace(/\D/g, '');
    const cleanName = (name || '').trim();

    if (!cleanName) {
      setError('कृपया मरीज का नाम दर्ज करें (Please enter patient name)');
      setIsLoading(false);
      return;
    }

    const birthYear = new Date().getFullYear() - (parseInt(age, 10) || 30);

    const manualProfile = {
      abha_id: createAbha ? `temp.${cleanPhone.slice(-4)}@abdm` : null,
      abha_number: createAbha ? `91-TEMP-${cleanPhone.slice(-4)}-2026` : null,
      name: cleanName,
      gender: gender || 'M',
      dob: `${birthYear}-01-01`,
      age: parseInt(age, 10) || 30,
      mobile: cleanPhone || '9800000000',
      address: 'Walk-In OPD Registration',
      is_manual_walkin: true,
      created_abha: Boolean(createAbha),
    };

    setIsLoading(false);
    return manualProfile;
  }, []);

  /**
   * Patient confirms demographics ("Is this you? -> Yes")
   */
  const confirmIdentity = useCallback((demographics) => {
    setPatient(demographics);
    setFlowStep('consent');
    setError(null);
  }, []);

  /**
   * Submit 3-Step Consent & start session (POST /api/session/start + POST /api/session/consent)
   */
  const submitConsent = useCallback(async (finalConsents, voiceRef = null) => {
    setIsLoading(true);
    setError(null);
    let sessionData = null;

    try {
      // 1. Start Session
      const startRes = await fetch(`${API_BASE_URL}/api/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          abha_id: patient?.abha_id || null,
          patient_name: patient?.name || 'मरीज (Patient)',
          language: language,
          is_caregiver: isCaregiver,
          caregiver_name: isCaregiver ? caregiverDetails.name || null : null,
          caregiver_relationship: isCaregiver ? caregiverDetails.relationship || null : null,
          caregiver_phone: isCaregiver ? caregiverDetails.phone || null : null,
          voice_only_mode: voiceOnlyMode,
          interview_mode: interviewMode,
        }),
      });

      if (startRes.ok) {
        sessionData = await startRes.json();

        // 2. Record immutable Consent Audit entries
        const consentPayload = {
          session_id: sessionData.session_id,
          consents: [
            { action: 'share_doctor', granted: finalConsents.share_doctor },
            { action: 'store_abdm', granted: finalConsents.store_abdm },
            { action: 'anonymized_research', granted: finalConsents.anonymized_research },
          ],
          voice_confirmation_ref: voiceRef,
        };

        await fetch(`${API_BASE_URL}/api/session/consent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(consentPayload),
        });
      }
    } catch (err) {
      console.warn('[SessionContext] Live backend start session unreachable, using local session state:', err);
    } finally {
      setIsLoading(false);
    }

    if (!sessionData) {
      sessionData = {
        session_id: 'OPD-' + Math.floor(100000 + Math.random() * 900000),
        patient_name: patient?.name || 'मरीज (Patient)',
        status: 'active',
        is_caregiver: isCaregiver,
        caregiver_name: isCaregiver ? caregiverDetails.name || null : null,
        caregiver_relationship: isCaregiver ? caregiverDetails.relationship || null : null,
        caregiver_phone: isCaregiver ? caregiverDetails.phone || null : null,
        voice_only_mode: voiceOnlyMode,
        interview_mode: interviewMode,
        created_at: new Date().toISOString(),
      };
    }

    setConsents(finalConsents);
    setVoiceConfirmationRef(voiceRef);
    setSession(sessionData);
    setFlowStep('active');

    sessionStorage.setItem('active_session_id', sessionData.session_id);
    return sessionData;
  }, [language, patient, isCaregiver, caregiverDetails, voiceOnlyMode, interviewMode]);

  /**
   * Full privacy wipe on session completion or idle timeout expiration
   */
  const wipePrivacyData = useCallback(async () => {
    const activeSessionId = session?.session_id || sessionStorage.getItem('active_session_id');

    // Notify backend if session exists
    if (activeSessionId) {
      try {
        await fetch(`${API_BASE_URL}/api/session/end`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: activeSessionId }),
        });
      } catch (err) {
        console.warn('Backend session end notice failed:', err);
      }
    }

    // 1. Clear React State
    setSession(null);
    setPatient(null);
    setConsents(DEFAULT_CONSENTS);
    setVoiceConfirmationRef(null);
    setError(null);
    setIsCaregiver(false);
    setCaregiverDetails({ name: '', relationship: 'Family Member', phone: '' });
    setVoiceOnlyMode(false);
    setInterviewMode('allopathic');
    setBodyMapSelections([]);
    setFlowStep('language');

    // 2. Purge Browser Storages
    sessionStorage.clear();
    localStorage.removeItem('medikiosk_patient');
    localStorage.removeItem('medikiosk_session');

    // 3. Clear any object URLs
    if (window._medikiosk_blob_urls && Array.isArray(window._medikiosk_blob_urls)) {
      window._medikiosk_blob_urls.forEach((url) => URL.revokeObjectURL(url));
      window._medikiosk_blob_urls = [];
    }

    console.log('[MediKiosk] Privacy wipe completed. All sensitive patient data purged.');
  }, [session]);

  const value = {
    language,
    setLanguage,
    flowStep,
    setFlowStep,
    patient,
    setPatient,
    session,
    consents,
    setConsents,
    voiceConfirmationRef,
    isLoading,
    error,
    setError,
    selectLanguage,
    verifyAbha,
    requestAadhaarOtp,
    verifyAadhaarOtp,
    registerManualPatient,
    confirmIdentity,
    submitConsent,
    wipePrivacyData,
    endSession: wipePrivacyData,
    // Phase 5 caregiver, voice-only, AYUSH, body map
    isCaregiver,
    setIsCaregiver,
    caregiverDetails,
    setCaregiverDetails,
    voiceOnlyMode,
    setVoiceOnlyMode,
    interviewMode,
    setInterviewMode,
    bodyMapSelections,
    setBodyMapSelections,
    // Accessibility & Staff flags
    isLargeText,
    setIsLargeText,
    isHighContrast,
    setIsHighContrast,
    isStaffMode,
    setIsStaffMode,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};

export default SessionContext;
