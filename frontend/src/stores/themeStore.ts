import { create } from 'zustand';

type Theme = 'dark' | 'light';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
}

function getInitialTheme(): Theme {
  const saved = localStorage.getItem('theme');
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
  const html = document.documentElement;
  if ((document as any).startViewTransition) {
    (document as any).startViewTransition(() => {
      html.classList.toggle('dark', theme === 'dark');
    });
  } else {
    html.classList.toggle('dark', theme === 'dark');
  }
}

const initial = getInitialTheme();
applyTheme(initial);

export const useThemeStore = create<ThemeState>((set) => ({
  theme: initial,
  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', next);
      applyTheme(next);
      return { theme: next };
    }),
  setTheme: (t) => {
    localStorage.setItem('theme', t);
    applyTheme(t);
    set({ theme: t });
  },
}));
