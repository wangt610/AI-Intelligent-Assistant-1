export function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center text-text-muted select-none">
      <div className="text-center animate-fade-in">
        <div className="text-5xl mb-4 opacity-20">✨</div>
        <h3 className="font-heading text-base font-medium text-text-secondary mb-2">开始一段新对话</h3>
        <p className="text-xs text-text-muted">
          选择或创建一个对话，或按{' '}
          <kbd className="px-1.5 py-0.5 text-[10px] rounded bg-surface border border-border font-label">
            Ctrl+K
          </kbd>{' '}
          打开命令面板
        </p>
      </div>
    </div>
  );
}
