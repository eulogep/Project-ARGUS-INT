// ==============================================================================
// Project ARGUS-INT - Client Layout Wrapper
// Binds UI store preferences (density, blur, effects) to HTML datasets
// ==============================================================================

'use client';

import React, { useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { Footer } from './Footer';
import { useAppStore } from '@/lib/store';
import { usePanicMode } from '@/hooks/usePanicMode';

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const { privacyBlur, dataDensity, effectsEnabled } = useAppStore();

  // Activate Panic Mode global keyboard listener
  usePanicMode();

  useEffect(() => {
    // Inject datasets onto html / body for globals.css selectors
    const root = document.documentElement;
    root.setAttribute('data-density', dataDensity);
    root.setAttribute('data-privacy', privacyBlur ? 'blur' : 'clear');
    root.setAttribute('data-effects', effectsEnabled ? 'on' : 'off');
  }, [dataDensity, privacyBlur, effectsEnabled]);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-wrapper">
        <TopBar />
        <main className="main-content">{children}</main>
        <Footer />
      </div>
    </div>
  );
}
export default ClientLayout;
