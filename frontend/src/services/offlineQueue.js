/**
 * Client-Side Offline Queue & Auto-Sync Engine
 * PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
 * Dev 2 Offline Resilient Infrastructure
 */

const DB_NAME = 'medikiosk_offline_db';
const STORE_NAME = 'mutation_queue';
const DB_VERSION = 1;

class OfflineQueueService {
  constructor() {
    this.isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;
    this.listeners = new Set();
    this.isSyncing = false;
    this.healthInterval = null;
    this.apiBase = 'http://localhost:8000';

    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => this.handleNetworkChange(true));
      window.addEventListener('offline', () => this.handleNetworkChange(false));
      this.startHealthPolling();
    }
  }

  // --------------------------------------------------------------------------
  // IndexedDB Helpers
  // --------------------------------------------------------------------------

  async openDB() {
    if (typeof indexedDB === 'undefined') return null;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Queues an API mutation into IndexedDB.
   * @param {Object} item - { url, method, body, headers, timestamp }
   */
  async enqueue(item) {
    const queueItem = {
      ...item,
      timestamp: Date.now(),
      status: 'pending',
    };

    try {
      const db = await this.openDB();
      if (db) {
        await new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const store = tx.objectStore(STORE_NAME);
          store.add(queueItem);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
      } else {
        // LocalStorage fallback
        const existing = JSON.parse(localStorage.getItem(STORE_NAME) || '[]');
        existing.push({ ...queueItem, id: Date.now() });
        localStorage.setItem(STORE_NAME, JSON.stringify(existing));
      }
      this.notify();
    } catch (e) {
      console.warn('Failed to enqueue offline item:', e);
    }
  }

  /**
   * Retrieves all pending queued items in chronological order.
   */
  async getQueue() {
    try {
      const db = await this.openDB();
      if (db) {
        return new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readonly');
          const store = tx.objectStore(STORE_NAME);
          const request = store.getAll();
          request.onsuccess = () => resolve(request.result || []);
          request.onerror = () => reject(request.error);
        });
      } else {
        return JSON.parse(localStorage.getItem(STORE_NAME) || '[]');
      }
    } catch (e) {
      return [];
    }
  }

  /**
   * Clears an item from the queue after successful sync.
   */
  async dequeue(id) {
    try {
      const db = await this.openDB();
      if (db) {
        await new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const store = tx.objectStore(STORE_NAME);
          store.delete(id);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
      } else {
        const existing = JSON.parse(localStorage.getItem(STORE_NAME) || '[]');
        const filtered = existing.filter((item) => item.id !== id);
        localStorage.setItem(STORE_NAME, JSON.stringify(filtered));
      }
      this.notify();
    } catch (e) {
      console.warn('Failed to dequeue item:', e);
    }
  }

  async getPendingCount() {
    const queue = await this.getQueue();
    return queue.length;
  }

  // --------------------------------------------------------------------------
  // Auto-Sync Execution
  // --------------------------------------------------------------------------

  async sync() {
    if (this.isSyncing) return;
    const queue = await this.getQueue();
    if (queue.length === 0) return;

    this.isSyncing = true;
    this.notify({ isSyncing: true });

    for (const item of queue) {
      try {
        const res = await fetch(item.url, {
          method: item.method || 'POST',
          headers: item.headers || { 'Content-Type': 'application/json' },
          body: typeof item.body === 'string' ? item.body : JSON.stringify(item.body),
        });

        if (res.ok) {
          await this.dequeue(item.id);
        } else if (res.status >= 400 && res.status < 500) {
          // Client error, cannot retry forever -> discard
          await this.dequeue(item.id);
        } else {
          // Server error -> break and retry on next health check
          break;
        }
      } catch (err) {
        // Network still unreachable
        this.isOnline = false;
        break;
      }
    }

    this.isSyncing = false;
    this.notify({ isSyncing: false, synced: true });
  }

  // --------------------------------------------------------------------------
  // Health Check & Polling
  // --------------------------------------------------------------------------

  startHealthPolling() {
    if (this.healthInterval) clearInterval(this.healthInterval);

    this.healthInterval = setInterval(async () => {
      try {
        const res = await fetch(`${this.apiBase}/api/health`, { method: 'GET', cache: 'no-store' });
        if (res.ok) {
          if (!this.isOnline) {
            this.handleNetworkChange(true);
          }
        } else {
          if (this.isOnline) {
            this.handleNetworkChange(false);
          }
        }
      } catch (err) {
        if (this.isOnline) {
          this.handleNetworkChange(false);
        }
      }
    }, 10000);
  }

  handleNetworkChange(online) {
    this.isOnline = online;
    this.notify();
    if (online) {
      this.sync();
    }
  }

  // --------------------------------------------------------------------------
  // Event Subscription
  // --------------------------------------------------------------------------

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async notify(extra = {}) {
    const count = await this.getPendingCount();
    const state = {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      pendingCount: count,
      ...extra,
    };
    for (const listener of this.listeners) {
      listener(state);
    }
  }
}

export const offlineQueue = new OfflineQueueService();
