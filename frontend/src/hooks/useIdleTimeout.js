import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * useIdleTimeout — Touch & interaction timeout management for public kiosk security.
 *
 * @param {number} timeoutMs - Total inactivity time before session reset (default: 90,000ms / 1.5 min)
 * @param {number} warningMs - Warning threshold before timeout (default: 30,000ms / 30 sec)
 * @param {function} onTimeout - Callback fired when timeout expires to wipe state
 */
export const useIdleTimeout = ({
  timeoutMs = 90000,
  warningMs = 30000,
  onTimeout = () => {},
}) => {
  const [isWarningActive, setIsWarningActive] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(Math.round(warningMs / 1000));
  const [totalSecondsLeft, setTotalSecondsLeft] = useState(Math.round(timeoutMs / 1000));

  const timeoutTimerRef = useRef(null);
  const warningTimerRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  const totalCountdownIntervalRef = useRef(null);

  const resetTimer = useCallback(() => {
    if (timeoutTimerRef.current) clearTimeout(timeoutTimerRef.current);
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    if (totalCountdownIntervalRef.current) clearInterval(totalCountdownIntervalRef.current);

    setIsWarningActive(false);
    setSecondsRemaining(Math.round(warningMs / 1000));
    setTotalSecondsLeft(Math.round(timeoutMs / 1000));

    // Continuous total countdown interval for live header timer
    let totalLeft = Math.round(timeoutMs / 1000);
    totalCountdownIntervalRef.current = setInterval(() => {
      totalLeft -= 1;
      setTotalSecondsLeft(Math.max(0, totalLeft));
      if (totalLeft <= 0) {
        clearInterval(totalCountdownIntervalRef.current);
      }
    }, 1000);

    // Schedule warning modal
    const warningDelay = Math.max(0, timeoutMs - warningMs);
    warningTimerRef.current = setTimeout(() => {
      setIsWarningActive(true);
      let count = Math.round(warningMs / 1000);
      setSecondsRemaining(count);

      countdownIntervalRef.current = setInterval(() => {
        count -= 1;
        setSecondsRemaining(Math.max(0, count));
        if (count <= 0) {
          clearInterval(countdownIntervalRef.current);
        }
      }, 1000);
    }, warningDelay);

    // Schedule expiration
    timeoutTimerRef.current = setTimeout(() => {
      setIsWarningActive(false);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      if (totalCountdownIntervalRef.current) clearInterval(totalCountdownIntervalRef.current);
      onTimeout();
    }, timeoutMs);
  }, [timeoutMs, warningMs, onTimeout]);

  // Listen to kiosk user interaction events
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
      if (totalCountdownIntervalRef.current) clearInterval(totalCountdownIntervalRef.current);
    };
  }, [resetTimer, isWarningActive]);

  const extendSession = () => {
    resetTimer();
  };

  return {
    isWarningActive,
    secondsRemaining,
    totalSecondsLeft,
    extendSession,
  };
};

export default useIdleTimeout;
