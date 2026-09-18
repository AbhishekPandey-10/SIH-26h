import React, { useEffect, useState } from 'react';
import { offlineQueue } from '../../services/offlineQueue';

export default function OfflineIndicator() {
  const [status, setStatus] = useState({
    isOnline: true,
    isSyncing: false,
    pendingCount: 0,
    synced: false,
  });
  const [showSyncedNotice, setShowSyncedNotice] = useState(false);

  useEffect(() => {
    const unsubscribe = offlineQueue.subscribe((newStatus) => {
      setStatus(newStatus);
      if (newStatus.synced) {
        setShowSyncedNotice(true);
        const timer = setTimeout(() => setShowSyncedNotice(false), 4000);
        return () => clearTimeout(timer);
      }
    });

    offlineQueue.getPendingCount().then((count) => {
      setStatus((prev) => ({ ...prev, pendingCount: count }));
    });

    return unsubscribe;
  }, []);

  if (status.isOnline && !status.isSyncing && !showSyncedNotice && status.pendingCount === 0) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        fontWeight: 600,
        fontSize: '14px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        transition: 'all 0.3s ease',
        backgroundColor: !status.isOnline
          ? '#dc2626'
          : status.isSyncing
          ? '#2563eb'
          : '#16a34a',
        color: '#ffffff',
      }}
    >
      {!status.isOnline && (
        <>
          <span style={{ fontSize: '18px' }}>⚡</span>
          <span>
            ऑफ़लाइन मोड (Offline Mode) — नेटवर्क कनेक्शन नहीं है।
            {status.pendingCount > 0 ? ` ${status.pendingCount} क्रियाएं कतार में हैं (Actions queued).` : ''}
            नेटवर्क वापस आने पर डेटा स्वतः सिंक हो जाएगा।
          </span>
        </>
      )}

      {status.isOnline && status.isSyncing && (
        <>
          <span style={{ animation: 'spin 1s linear infinite' }}>🔄</span>
          <span>
            सिंक हो रहा है (Syncing {status.pendingCount} queued records to hospital server)...
          </span>
        </>
      )}

      {status.isOnline && !status.isSyncing && showSyncedNotice && (
        <>
          <span>✅</span>
          <span>इंटरनेट पुनः कनेक्ट हुआ। सभी रिकॉर्ड्स सिंक हो गए हैं (All offline records synced).</span>
        </>
      )}
    </div>
  );
}
