import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Session, Message, FileInfo, SearchSource } from '../types/session';
import * as sessionsApi from '../services/sessions';
import { useUIStore } from './uiStore';

interface SessionState {
  sessions: Session[];
  currentSessionId: string | null;
  messages: Message[];
  loading: boolean;
  messagesLoading: boolean;
  loaded: boolean;
  interruptedMessage: { messageId: number; userMessage: string } | null;

  loadSessions: () => Promise<void>;
  setCurrentSession: (id: string | null) => Promise<void>;
  createSession: () => Promise<string>;
  deleteSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  searchSessions: (q: string) => Promise<void>;
  editMessage: (messageId: number, content: string) => Promise<void>;
  deleteMessage: (messageId: number) => Promise<void>;
  appendMessage: (msg: Message) => void;
  updateLastAssistantMessage: (content: string) => void;
  updateLastAssistantSearchSources: (sources: SearchSource[]) => void;
  updateLastUserMessageFileInfo: (info: FileInfo) => void;
  clearCurrentSessionMessages: () => void;
  clearInterruptedMessage: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  loading: false,
  messagesLoading: false,
  loaded: false,
  interruptedMessage: null,

  loadSessions: async () => {
    set({ loading: true });
    try {
      const { currentSessionId } = get();
      // 并行获取会话列表和消息（currentSessionId 已由 persist 恢复）
      const [sessions, messages] = await Promise.all([
        sessionsApi.fetchSessions(),
        currentSessionId ? sessionsApi.fetchMessages(currentSessionId) : Promise.resolve(null),
      ]);
      set({ sessions, loaded: true, loading: false });
      if (currentSessionId && messages && sessions.some((s) => s.id === currentSessionId)) {
        const lastMsg = messages[messages.length - 1];
        if (lastMsg?.role === 'assistant' && lastMsg?.status === 'interrupted') {
          const userMsg = messages[messages.length - 2];
          set({
            messages,
            interruptedMessage: userMsg?.role === 'user'
              ? { messageId: lastMsg.id, userMessage: userMsg.content }
              : null,
          });
        } else {
          set({ messages });
        }
      }
    } catch {
      set({ loading: false });
      useUIStore.getState().addToast('加载会话列表失败', 'error');
    }
  },

  setCurrentSession: async (id) => {
    set({ currentSessionId: id, messages: [], interruptedMessage: null });
    if (!id) return;
    set({ messagesLoading: true });
    try {
      const messages = await sessionsApi.fetchMessages(id);
      // 检测最后一条消息是否被中断
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === 'assistant' && lastMsg?.status === 'interrupted') {
        // 找到中断消息对应的用户消息（前一条）
        const userMsg = messages[messages.length - 2];
        if (userMsg?.role === 'user') {
          set({
            messages,
            messagesLoading: false,
            interruptedMessage: { messageId: lastMsg.id, userMessage: userMsg.content },
          });
          return;
        }
      }
      set({ messages, messagesLoading: false });
    } catch {
      set({ messagesLoading: false });
      useUIStore.getState().addToast('加载消息失败', 'error');
    }
  },

  createSession: async () => {
    const session = await sessionsApi.createSession();
    set((s) => ({ sessions: [session, ...s.sessions] }));
    return session.id;
  },

  deleteSession: async (id) => {
    await sessionsApi.deleteSession(id);
    set((s) => {
      const sessions = s.sessions.filter((x) => x.id !== id);
      const currentSessionId = s.currentSessionId === id ? null : s.currentSessionId;
      return { sessions, currentSessionId, messages: currentSessionId ? s.messages : [] };
    });
  },

  renameSession: async (id, title) => {
    await sessionsApi.renameSession(id, title);
    set((s) => ({
      sessions: s.sessions.map((x) => (x.id === id ? { ...x, title } : x)),
    }));
  },

  searchSessions: async (q) => {
    if (!q.trim()) {
      const sessions = await sessionsApi.fetchSessions();
      set({ sessions });
      return;
    }
    const sessions = await sessionsApi.searchSessions(q);
    set({ sessions });
  },

  editMessage: async (messageId, content) => {
    const { currentSessionId } = get();
    if (!currentSessionId) return;
    await sessionsApi.editMessage(currentSessionId, messageId, content);
    set((s) => {
      const idx = s.messages.findIndex((m) => m.id === messageId);
      if (idx === -1) return s;
      const messages = s.messages.slice(0, idx + 1).map((m, i) =>
        i === idx ? { ...m, content } : m,
      );
      return { messages };
    });
  },

  deleteMessage: async (messageId) => {
    const { currentSessionId } = get();
    if (!currentSessionId) return;
    await sessionsApi.deleteMessage(currentSessionId, messageId);
    set((s) => {
      const idx = s.messages.findIndex((m) => m.id === messageId);
      if (idx === -1) return s;
      return { messages: s.messages.slice(0, idx) };
    });
  },

  appendMessage: (msg) => {
    set((s) => ({ messages: [...s.messages, msg] }));
  },

  updateLastUserMessageFileInfo: (info) => {
    set((s) => {
      const messages = [...s.messages];
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'user') {
          messages[i] = { ...messages[i], file_info: info };
          break;
        }
      }
      return { messages };
    });
  },

  updateLastAssistantMessage: (chunk) => {
    set((s) => {
      const messages = [...s.messages];
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant') {
          messages[i] = { ...messages[i], content: messages[i].content + chunk };
          break;
        }
      }
      return { messages };
    });
  },

  updateLastAssistantSearchSources: (sources) => {
    set((s) => {
      const messages = [...s.messages];
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'assistant') {
          messages[i] = { ...messages[i], search_sources: sources };
          break;
        }
      }
      return { messages };
    });
  },

  clearCurrentSessionMessages: () => set({ messages: [] }),
  clearInterruptedMessage: () => set({ interruptedMessage: null }),
}),
{
  name: 'session-storage',
  partialize: (state) => ({ currentSessionId: state.currentSessionId }),
},
),
);
