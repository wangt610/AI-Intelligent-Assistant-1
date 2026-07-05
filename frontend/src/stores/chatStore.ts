import { create } from 'zustand';
import type { ModelItem, ModelSource } from '../types/model';
import type { RAGSource } from '../types/chat';
import { apiStream, apiStreamFormData } from '../services/api';
import { useSessionStore } from './sessionStore';

interface ChatState {
  input: string;
  streaming: boolean;
  thinking: string;
  ragSources: RAGSource[];
  currentRagMode: 'off' | 'auto' | 'force';
  webSearchEnabled: boolean;
  showThinking: boolean;
  searchAvailable: boolean;
  warmLoading: boolean;

  models: ModelItem[];
  modelSources: ModelSource[];
  selectedModelId: string;
  selectedModelSource: string;

  abortController: AbortController | null;

  setInput: (v: string) => void;
  setStreaming: (v: boolean) => void;
  setThinking: (v: string) => void;
  setRagSources: (sources: RAGSource[]) => void;
  toggleRagMode: () => void;
  toggleWebSearch: () => void;
  toggleThinking: () => void;
  setSelectedModel: (id: string, source: string) => void;
  setModels: (models: ModelItem[]) => void;
  setModelSources: (sources: ModelSource[]) => void;
  sendMessage: (sessionId: string, message: string) => void;
  sendFileMessage: (sessionId: string, message: string, file: File) => void;
  regenerate: (sessionId: string) => void;
  stopStreaming: () => void;
  resetChat: () => void;
  setSearchAvailable: (v: boolean) => void;
  setWarmLoading: (v: boolean) => void;
  retryInterruptedMessage: (sessionId: string, message: string) => void;
}

/** rAF 节流的 token 累加器 — 将 50ms 窗口内的 token 合并为一次 setState */
function createBufferedUpdate(update: (text: string) => void): (text: string) => void {
  let buffer = '';
  let scheduled = false;
  const flush = () => {
    scheduled = false;
    if (buffer) {
      update(buffer);
      buffer = '';
    }
  };
  return (text: string) => {
    buffer += text;
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(flush);
    }
  };
}

/** 统一的 SSE 事件处理器，消除 sendMessage/sendFileMessage/regenerate/retryInterruptedMessage 中的重复回调 */
function createSSEHandlers(
  updateLastAssistantMessage: (token: string) => void,
) {
  const bufferedUpdate = createBufferedUpdate(updateLastAssistantMessage);
  return {
    onEvent: (event: string, data: string) => {
      switch (event) {
        case 'thinking':
          try { useChatStore.setState((s) => ({ thinking: s.thinking + JSON.parse(data).text })); } catch {}
          break;
        case 'token':
          try { bufferedUpdate(JSON.parse(data).token); } catch {}
          break;
        case 'rag_sources':
          try { useChatStore.setState({ ragSources: JSON.parse(data).sources || [] }); } catch {}
          break;
        case 'search_sources':
          try { useSessionStore.getState().updateLastAssistantSearchSources(JSON.parse(data)); } catch {}
          break;
        case 'done':
          useChatStore.setState({ streaming: false });
          break;
        case 'error':
          try {
            bufferedUpdate(`错误: ${JSON.parse(data).detail}`);
          } catch {
            bufferedUpdate(`错误: ${data}`);
          }
          useChatStore.setState({ streaming: false });
          break;
      }
    },
    onError: (err: Error) => {
      bufferedUpdate(`错误: ${err.message}`);
      useChatStore.setState({ streaming: false });
    },
    onComplete: () => {
      useChatStore.setState({ streaming: false });
    },
  };
}

export const useChatStore = create<ChatState>((set, get) => ({
  input: '',
  streaming: false,
  thinking: '',
  ragSources: [],
  currentRagMode: 'auto',
  webSearchEnabled: false,
  showThinking: true,
  searchAvailable: false,
  warmLoading: false,

  models: [],
  modelSources: [],
  selectedModelId: '',
  selectedModelSource: 'ollama',

  abortController: null,

  setInput: (v) => set((s) => ({ input: typeof v === 'function' ? (v as (prev: string) => string)(s.input) : v })),
  setStreaming: (v) => set({ streaming: v }),
  setThinking: (v) => set({ thinking: v }),
  setRagSources: (sources) => set({ ragSources: sources }),
  toggleRagMode: () =>
    set((s) => ({
      currentRagMode: s.currentRagMode === 'off' ? 'auto' : s.currentRagMode === 'auto' ? 'force' : 'off',
    })),
  toggleWebSearch: () => set((s) => ({ webSearchEnabled: !s.webSearchEnabled })),
  toggleThinking: () => set((s) => ({ showThinking: !s.showThinking })),
  setSelectedModel: (id, source) => set({ selectedModelId: id, selectedModelSource: source }),
  setModels: (models) => set({ models }),
  setModelSources: (sources) => set({ modelSources: sources }),
  setSearchAvailable: (v) => set({ searchAvailable: v }),
  setWarmLoading: (v) => set({ warmLoading: v }),

  sendMessage: (sessionId, message) => {
    const { showThinking, currentRagMode, webSearchEnabled, selectedModelId, selectedModelSource } = get();
    const { appendMessage, updateLastAssistantMessage } = useSessionStore.getState();

    // Append user message
    appendMessage({ id: 0, session_id: sessionId, role: 'user', content: message, timestamp: new Date().toISOString() });
    // Placeholder for assistant
    appendMessage({ id: -1, session_id: sessionId, role: 'assistant', content: '', timestamp: new Date().toISOString() });

    set({ streaming: true, thinking: '', ragSources: [] });

    const { onEvent, onError, onComplete } = createSSEHandlers(updateLastAssistantMessage);
    const ctrl = apiStream(
      '/chat',
      {
        session_id: sessionId,
        message,
        show_thinking: showThinking,
        rag_mode: currentRagMode,
        web_search: webSearchEnabled,
        model_source: selectedModelSource || undefined,
        model_id: selectedModelId || undefined,
      },
      onEvent,
      onError,
      onComplete,
    );

    set({ abortController: ctrl });
  },

  sendFileMessage: (sessionId, message, file) => {
    const { showThinking, currentRagMode, webSearchEnabled, selectedModelId, selectedModelSource } = get();
    const { appendMessage, updateLastAssistantMessage, updateLastUserMessageFileInfo } = useSessionStore.getState();

    appendMessage({
      id: 0, session_id: sessionId, role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    });
    appendMessage({
      id: -1, session_id: sessionId, role: 'assistant', content: '',
      timestamp: new Date().toISOString(),
    });

    set({ streaming: true, thinking: '', ragSources: [] });

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('message', message);
    formData.append('file', file);
    formData.append('show_thinking', String(showThinking));
    formData.append('rag_mode', currentRagMode);
    formData.append('web_search', String(webSearchEnabled));
    formData.append('model_source', selectedModelSource || 'ollama');
    formData.append('model_id', selectedModelId || '');

    const { onEvent, onError, onComplete } = createSSEHandlers(updateLastAssistantMessage);
    const ctrl = apiStreamFormData(
      '/chat/upload',
      formData,
      (event, data) => {
        if (event === 'file_info') {
          try { updateLastUserMessageFileInfo(JSON.parse(data)); } catch {}
        } else {
          onEvent(event, data);
        }
      },
      onError,
      onComplete,
    );

    set({ abortController: ctrl });
  },

  regenerate: (sessionId) => {
    const { showThinking, currentRagMode, webSearchEnabled, selectedModelId, selectedModelSource } = get();
    const { messages, appendMessage, updateLastAssistantMessage } = useSessionStore.getState();

    // Remove last assistant message(s) locally, backend will also delete them from DB
    const lastUserIdx = messages.map((m) => m.role === 'user').lastIndexOf(true);
    const trimmed = lastUserIdx >= 0 ? messages.slice(0, lastUserIdx + 1) : messages;
    useSessionStore.setState({ messages: trimmed });

    appendMessage({ id: -2, session_id: sessionId, role: 'assistant', content: '', timestamp: new Date().toISOString() });

    set({ streaming: true, thinking: '', ragSources: [] });

    const { onEvent, onError, onComplete } = createSSEHandlers(updateLastAssistantMessage);
    const ctrl = apiStream(
      '/chat/regenerate',
      {
        session_id: sessionId,
        show_thinking: showThinking,
        rag_mode: currentRagMode,
        web_search: webSearchEnabled,
        model_source: selectedModelSource || undefined,
        model_id: selectedModelId || undefined,
      },
      onEvent,
      onError,
      onComplete,
    );

    set({ abortController: ctrl });
  },

  stopStreaming: () => {
    const { abortController } = get();
    abortController?.abort();
    set({ streaming: false, abortController: null });
  },

  resetChat: () => set({
    input: '',
    streaming: false,
    thinking: '',
    ragSources: [],
    abortController: null,
  }),

  retryInterruptedMessage: (sessionId, message) => {
    const { showThinking, currentRagMode, webSearchEnabled, selectedModelId, selectedModelSource } = get();
    const { appendMessage, updateLastAssistantMessage, clearInterruptedMessage } = useSessionStore.getState();

    // 清除中断标记
    clearInterruptedMessage();

    // 添加新的助手占位
    appendMessage({ id: -1, session_id: sessionId, role: 'assistant', content: '', timestamp: new Date().toISOString() });

    set({ streaming: true, thinking: '', ragSources: [] });

    const { onEvent, onError, onComplete } = createSSEHandlers(updateLastAssistantMessage);
    const ctrl = apiStream(
      '/chat',
      {
        session_id: sessionId,
        message,
        show_thinking: showThinking,
        rag_mode: currentRagMode,
        web_search: webSearchEnabled,
        model_source: selectedModelSource || undefined,
        model_id: selectedModelId || undefined,
      },
      onEvent,
      onError,
      onComplete,
    );

    set({ abortController: ctrl });
  },
}));
