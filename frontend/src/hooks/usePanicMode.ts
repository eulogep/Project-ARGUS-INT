// ==============================================================================
// ARGUS-INT — Panic Mode Hook (Kill Switch)
// ESC×3 rapid press → wipe all data → redirect to neutral page
// ==============================================================================

'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '@/lib/store';

const PANIC_KEY = 'Escape';
const PANIC_COMBO_COUNT = 3;
const PANIC_WINDOW_MS = 1500;
const REDIRECT_URL = 'about:blank';

export function usePanicMode() {
  const pressTimestamps = useRef<number[]>([]);
  const wipeAllData = useAppStore((s) => s.wipeAllData);

  const executePanic = useCallback(() => {
    // 1. Wipe all stores (IndexedDB, localStorage, sessionStorage)
    wipeAllData();

    // 2. Clear all cookies
    document.cookie.split(';').forEach((c) => {
      document.cookie = c
        .replace(/^ +/, '')
        .replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
    });

    // 3. Close any open WebSocket connections
    window.dispatchEvent(new CustomEvent('argus:panic'));

    // 4. Replace page with blank and redirect
    document.body.innerHTML = '';
    document.body.style.background = '#000';

    // Use replace to prevent back-button access
    setTimeout(() => {
      window.location.replace(REDIRECT_URL);
    }, 50);
  }, [wipeAllData]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== PANIC_KEY) return;

      const now = Date.now();
      pressTimestamps.current.push(now);

      // Keep only recent presses within the window
      pressTimestamps.current = pressTimestamps.current.filter(
        (t) => now - t < PANIC_WINDOW_MS
      );

      if (pressTimestamps.current.length >= PANIC_COMBO_COUNT) {
        pressTimestamps.current = [];
        executePanic();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [executePanic]);
}
