import { useEffect } from 'react';
import { useUIStore } from '../stores/uiStore';
import { useSessionStore } from '../stores/sessionStore';

export function useKeyboardShortcuts() {
  const setShortcutSheetOpen = useUIStore((s) => s.setShortcutSheetOpen);
  const closeAll = useUIStore((s) => s.closeAll);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const createSession = useSessionStore((s) => s.createSession);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      if (e.key === '?' && !isInput) {
        e.preventDefault();
        setShortcutSheetOpen(true);
        return;
      }

      if (e.key === 'Escape') {
        closeAll();
        return;
      }

      if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        const input = document.querySelector<HTMLTextAreaElement>('#messageInput');
        input?.focus();
        return;
      }

      if (e.ctrlKey && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        createSession();
        return;
      }

      if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        toggleSidebar();
        return;
      }
    }

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setShortcutSheetOpen, closeAll, toggleSidebar, createSession]);
}
