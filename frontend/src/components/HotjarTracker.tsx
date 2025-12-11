import { useHotjar } from '../hooks/useHotjar';

/**
 * Component that initializes Hotjar tracking for the application
 * Must be used inside Router context
 */
export const HotjarTracker = () => {
  useHotjar();
  return null;
};