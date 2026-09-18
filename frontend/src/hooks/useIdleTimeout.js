import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * useIdleTimeout — Touch & interaction timeout management for kiosk security.
 *
 * @param {number} timeoutMs - Inactivity time before session reset (default: 180,000ms / 3 min)
 * @param {number} warningMs - Time before timeout to show warning (default: 30,000ms / 30 sec)
 * @param {function} onTimeout - Callback fired when timeout completely expires
 */
export const useIdleTimeout = ({
  timeoutMs = 180000,
  warningMs = 30000,
  onTimeout = () => {},
}) => {
  const [isWarningActive, setIsWarningActive] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(Math.round(warningMs / 1000));

  const timeoutTimerRef = useRef(null);
  const warningTimerRef = useRef(null);
  const countdownIntervalRef = useRef(null);

  const resetTimer = useCallback(() => {
    // Clear existing timers
    if (timeoutTimerRef.current) clearTimeout(timeoutTimerRef.current);
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);

    setIsWarningActive(false);
    setSecondsRemaining(Math.round(warningMs / 1000));

    // Schedule warning modal
    const warningDelay = Math.max(0, timeoutMs - warningMs);
    warningTimerRef.current = setTimeout(() => {
      setIsWarningActive(true);
      let count = Math.round(warningMs / 1000);
      setSecondsRemaining(count);

      countdownIntervalRef.current = setInterval(() => {
        count -= 1;
        setSecondsRemaining(count);
        if (count <= 0) {
          clearInterval(countdownIntervalRef.current);
        }
      }, 1000);
    }, warningDelay);

    // Schedule expiration
    timeoutTimerRef.current = setTimeout(() => {
      setIsWarningActive(false);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      onTimeout();
    }, timeoutMs);
  }, [timeoutMs, warningMs, onTimeout]);

  // Listen to common kiosk interaction events
  useEffect(() => {
    const events = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'scroll', 'click'];
    const handleActivity = () => {
      if (!isWarningActive) {
        resetTimer();
      }
    };

    events.forEach((evt) => window.addEventListener(evt, handleActivity));
    resetTimer();

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, handleActivity));
      if (timeoutTimerRef.current) clearTimeout(timeoutTimerRef.current);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [resetTimer, isWarningActive]);

  const extendSession = () => {
    resetTimer();
  };

  return {
    isWarningActive,
    secondsRemaining,
    extendSession,
  };
};

export default useIdleTimeout;
