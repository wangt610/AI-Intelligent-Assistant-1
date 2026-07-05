import { useEffect, useRef } from 'react';

export function useDraftAutoSave(
  sessionId: string | null,
  input: string,
) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (!sessionId) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(`draft_${sessionId}`, input);
      } catch { /* ignore */ }
    }, 500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [sessionId, input]);

  const loadDraft = (sessionId: string): string => {
    try {
      return localStorage.getItem(`draft_${sessionId}`) || '';
    } catch {
      return '';
    }
  };

  const clearDraft = (sessionId: string) => {
    try {
      localStorage.removeItem(`draft_${sessionId}`);
    } catch { /* ignore */ }
  };

  return { loadDraft, clearDraft };
}
