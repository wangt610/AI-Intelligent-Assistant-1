import { useUIStore } from '../../stores/uiStore';

const shortcuts = [
  { keys: 'Ctrl+K', desc: '命令面板' },
  { keys: '?', desc: '快捷键速查' },
  { keys: 'Ctrl+L', desc: '聚焦输入框' },
  { keys: 'Ctrl+Shift+N', desc: '新建对话' },
  { keys: 'Ctrl+B', desc: '切换侧边栏' },
  { keys: 'Escape', desc: '关闭面板' },
  { keys: 'Ctrl+Enter', desc: '发送消息' },
];

export function ShortcutCheatsheet() {
  const open = useUIStore((s) => s.shortcutSheetOpen);
  const setOpen = useUIStore((s) => s.setShortcutSheetOpen);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative bg-surface-elevated rounded shadow-2xl w-full max-w-sm border border-border p-5 animate-scale-in">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-heading font-semibold text-sm text-text">快捷键速查</h3>
          <button onClick={() => setOpen(false)} className="btn-icon" title="关闭">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div className="space-y-2">
          {shortcuts.map((s) => (
            <div key={s.keys} className="flex items-center justify-between py-1">
              <kbd className="px-2 py-1 text-xs font-label rounded bg-surface border border-border text-text">
                {s.keys}
              </kbd>
              <span className="text-xs font-label text-text-muted">{s.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
