import { useState, useEffect, useCallback } from 'react';

interface UseBackendCheckResult {
  isBackendAvailable: boolean;
  isChecking: boolean;
  error: string | null;
  checkBackend: () => Promise<void>;
}

export const useBackendCheck = (): UseBackendCheckResult => {
  const [isBackendAvailable, setIsBackendAvailable] = useState(true);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkBackend = useCallback(async () => {
    setIsChecking(true);
    setError(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const response = await fetch(
        `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/health`,
        {
          signal: controller.signal,
          method: 'GET',
        }
      );

      clearTimeout(timeoutId);

      if (response.ok) {
        setIsBackendAvailable(true);
        setError(null);
      } else {
        setIsBackendAvailable(false);
        setError(`Server responded with status: ${response.status}`);
      }
    } catch (err: any) {
      setIsBackendAvailable(false);
      if (err.name === 'AbortError') {
        setError('Connection timeout - server may be starting up');
      } else {
        setError('Cannot connect to backend server');
      }
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend]);

  return {
    isBackendAvailable,
    isChecking,
    error,
    checkBackend,
  };
};