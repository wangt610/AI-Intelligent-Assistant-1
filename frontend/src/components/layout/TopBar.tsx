import { useUIStore } from '../../stores/uiStore';
import { useChatStore } from '../../stores/chatStore';
import { useSessionStore } from '../../stores/sessionStore';

export function TopBar() {
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const setSettingsOpen = useUIStore((s) => s.setSettingsOpen);
  const showThinking = useChatStore((s) => s.showThinking);
  const toggleThinking = useChatStore((s) => s.toggleThinking);
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const sessions = useSessionStore((s) => s.sessions);

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-border bg-surface shrink-0">
      {/* Left: menu toggle + session title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={() => setSidebarOpen(true)}
          className="btn-icon lg:hidden"
          title="打开侧边栏"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>

        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-text truncate">
            {currentSession?.title || '新对话'}
          </span>
        </div>
      </div>

      {/* Right: action buttons with labels */}
      <div className="flex items-center gap-1">
        {/* Toggle Thinking */}
        <button
          onClick={toggleThinking}
          className={`btn-ghost text-xs ${showThinking ? 'active' : ''}`}
          title="显示/隐藏思考过程"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.5 4.5-3 6l-1 1.5V18a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-1.5L6 15c-1.5-1.5-3-3.5-3-6a7 7 0 0 1 7-7z"/>
            <circle cx="9" cy="9" r="1" fill="currentColor"/>
            <circle cx="15" cy="9" r="1" fill="currentColor"/>
          </svg>
          思考
        </button>

        {/* Settings */}
        <button
          onClick={() => setSettingsOpen(true)}
          className="btn-ghost text-xs"
          title="设置"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          设置
        </button>
      </div>
    </header>
  );
}
