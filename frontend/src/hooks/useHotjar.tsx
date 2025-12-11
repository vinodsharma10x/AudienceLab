import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

declare global {
  interface Window {
    hj: (command: string, ...args: any[]) => void;
  }
}

/**
 * Custom hook to track route changes in Hotjar for SPA navigation
 * This ensures Hotjar properly tracks page views when users navigate
 * between routes without full page reloads
 */
export const useHotjar = () => {
  const location = useLocation();

  useEffect(() => {
    // Only track in production and if Hotjar is loaded
    if (typeof window !== 'undefined' &&
        window.hj &&
        window.location.hostname !== 'localhost' &&
        window.location.hostname !== '127.0.0.1') {

      // Trigger a virtual page view in Hotjar
      // This tells Hotjar that the user has navigated to a new "page"
      const virtualPagePath = location.pathname + location.search + location.hash;

      try {
        window.hj('stateChange', virtualPagePath);
        console.log('[Hotjar] Virtual page view tracked:', virtualPagePath);
      } catch (error) {
        console.error('[Hotjar] Error tracking page view:', error);
      }
    }
  }, [location]);
};