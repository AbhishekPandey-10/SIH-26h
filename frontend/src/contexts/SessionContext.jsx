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

  const [flowStep, setFlowStep] = useState('language'); // 'language' | 'identity' | 'consent' | 'active'
  const [patient, setPatient] = useState(null);
  const [session, setSession] = useState(null);
  const [consents, setConsents] = useState(DEFAULT_CONSENTS);
  const [voiceConfirmationRef, setVoiceConfirmationRef] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Keep language in sessionStorage for transient session restoration
  useEffect(() => {
    sessionStorage.setItem('kiosk_language', language);
  }, [language]);

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
   */
  const verifyAbha = useCallback(async (abhaId) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/session/verify-abha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ abha_id: abhaId.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to verify ABHA ID.');
      }

      const data = await res.json();
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Request Aadhaar OTP fallback (POST /api/session/aadhaar-otp)
   */
  const requestAadhaarOtp = useCallback(async (aadhaarNumber) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/session/aadhaar-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aadhaar_number: aadhaarNumber.replace(/\s+/g, '') }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to request Aadhaar OTP.');
      }

      return await res.json();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Verify Aadhaar OTP (POST /api/session/verify-aadhaar-otp)
   */
  const verifyAadhaarOtp = useCallback(async (txnId, otp, aadhaarNumber) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/session/verify-aadhaar-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          txn_id: txnId,
          otp: otp.trim(),
          aadhaar_number: aadhaarNumber.replace(/\s+/g, ''),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Invalid OTP. Please check and try again.');
      }

      return await res.json();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
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
    try {
      // 1. Start Session
      const startRes = await fetch(`${API_BASE_URL}/api/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          abha_id: patient?.abha_id || null,
          patient_name: patient?.name || 'मरीज (Patient)',
          language: language,
          is_caregiver: false,
        }),
      });

      if (!startRes.ok) {
        const errData = await startRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to start kiosk session.');
      }

      const sessionData = await startRes.json();

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

      setConsents(finalConsents);
      setVoiceConfirmationRef(voiceRef);
      setSession(sessionData);
      setFlowStep('active');

      sessionStorage.setItem('active_session_id', sessionData.session_id);
      return sessionData;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [language, patient]);

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
    confirmIdentity,
    submitConsent,
    wipePrivacyData,
    endSession: wipePrivacyData,
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
