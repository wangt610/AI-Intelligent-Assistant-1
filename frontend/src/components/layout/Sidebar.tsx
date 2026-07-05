import { useState, useEffect } from 'react';
import { useSessionStore } from '../../stores/sessionStore';
import { useUIStore } from '../../stores/uiStore';

export function Sidebar() {
  const sessions = useSessionStore((s) => s.sessions);
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const loading = useSessionStore((s) => s.loading);
  const loaded = useSessionStore((s) => s.loaded);
  const loadSessions = useSessionStore((s) => s.loadSessions);
  const setCurrentSession = useSessionStore((s) => s.setCurrentSession);
  const createSession = useSessionStore((s) => s.createSession);
  const deleteSession = useSessionStore((s) => s.deleteSession);
  const renameSession = useSessionStore((s) => s.renameSession);
  const searchSessions = useSessionStore((s) => s.searchSessions);
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  useEffect(() => {
    if (!loaded) loadSessions();
  }, [loaded, loadSessions]);

  const handleNew = async () => {
    const id = await createSession();
    setCurrentSession(id);
    setSearch('');
  };

  const handleSearch = (q: string) => {
    setSearch(q);
    searchSessions(q);
  };

  const handleRename = async (id: string) => {
    if (editTitle.trim()) {
      await renameSession(id, editTitle.trim());
    }
    setEditingId(null);
  };

  return (
    <>
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-20 lg:hidden animate-fade-in"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-30 w-72 flex flex-col bg-surface border-r border-border transition-transform duration-200 ease-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Header */}
        <div className="px-4 pt-4 pb-3">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-accent">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <span className="font-heading font-semibold text-sm tracking-tight text-text">
              AI 智能助手
            </span>
          </div>

          <button
            onClick={handleNew}
            className="btn-primary w-full justify-center text-sm"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新对话
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pb-2">
          <div className="relative">
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="搜索对话..."
              className="input-field pl-8 py-1.5 text-xs"
            />
          </div>
        </div>

        {/* Divider */}
        <div className="divider mx-3 mb-2" />

        {/* Session list */}
        <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
          {loading && !loaded && (
            <div className="flex items-center justify-center py-8">
              <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin"/>
            </div>
          )}
          {sessions.length === 0 && loaded && (
            <div className="text-center text-xs text-text-muted py-8 font-label">
              {search ? '无匹配对话' : '暂无对话'}
            </div>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer text-xs transition-all ${
                currentSessionId === s.id
                  ? 'bg-accent-subtle text-accent'
                  : 'text-text-secondary hover:bg-surface-hover hover:text-text'
              }`}
              onClick={() => {
                setCurrentSession(s.id);
                if (window.innerWidth < 1024) setSidebarOpen(false);
              }}
            >
              {editingId === s.id ? (
                <input
                  autoFocus
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={() => handleRename(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRename(s.id);
                    if (e.key === 'Escape') setEditingId(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="flex-1 bg-surface px-2 py-1 text-xs rounded border border-accent/50 outline-none text-text"
                />
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="shrink-0 opacity-40">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  <span className="flex-1 truncate font-medium">{s.title}</span>
                </>
              )}
              <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(s.id);
                    setEditTitle(s.title);
                  }}
                  className="btn-icon w-6 h-6"
                  title="重命名"
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('确定删除此对话？')) {
                      if (currentSessionId === s.id) useSessionStore.getState().clearCurrentSessionMessages();
                      deleteSession(s.id);
                    }
                  }}
                  className="btn-icon w-6 h-6 text-text-muted hover:text-error"
                  title="删除"
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
