import { create } from 'zustand';
import type { Toast } from '../types/settings';

interface UIState {
  sidebarOpen: boolean;
  settingsOpen: boolean;
  shortcutSheetOpen: boolean;
  themePanelOpen: boolean;
  modelDropdownOpen: boolean;
  toasts: Toast[];

  toggleSidebar: () => void;
  setSidebarOpen: (v: boolean) => void;
  setSettingsOpen: (v: boolean) => void;
  setShortcutSheetOpen: (v: boolean) => void;
  setThemePanelOpen: (v: boolean) => void;
  setModelDropdownOpen: (v: boolean) => void;
  addToast: (message: string, type?: Toast['type']) => void;
  removeToast: (id: string) => void;
  closeAll: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  settingsOpen: false,
  shortcutSheetOpen: false,
  themePanelOpen: false,
  modelDropdownOpen: false,
  toasts: [],

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  setSettingsOpen: (v) => set({ settingsOpen: v, shortcutSheetOpen: false }),
  setShortcutSheetOpen: (v) => set({ shortcutSheetOpen: v, settingsOpen: false }),
  setThemePanelOpen: (v) => set({ themePanelOpen: v }),
  setModelDropdownOpen: (v) => set({ modelDropdownOpen: v }),

  addToast: (message, type = 'info') => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 3500);
  },

  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  closeAll: () => set({
    shortcutSheetOpen: false,
    settingsOpen: false,
    themePanelOpen: false,
    modelDropdownOpen: false,
  }),
}));
