import { useState } from 'react';

interface Props {
  content: string;
  streaming: boolean;
}

export function ThinkingPanel({ content, streaming }: Props) {
  const [collapsed, setCollapsed] = useState(true);

  if (!content && !streaming) return null;

  return (
    <div className="mb-3 ml-10 animate-fade-in">
      <div className="rounded-lg border border-border overflow-hidden bg-surface-elevated shadow-sm">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 w-full px-3 py-2 text-xs font-label text-text-muted hover:text-text transition-all bg-surface-hover/50"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            className={`transition-transform duration-200 ${collapsed ? '' : 'rotate-90'}`}
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span className="text-accent">思考过程</span>
          {streaming && (
            <span className="flex gap-1 ml-auto">
              <span className="w-1 h-1 rounded-full bg-accent/60 animate-pulse" />
              <span className="w-1 h-1 rounded-full bg-accent/40 animate-pulse" style={{ animationDelay: '150ms' }} />
              <span className="w-1 h-1 rounded-full bg-accent/20 animate-pulse" style={{ animationDelay: '300ms' }} />
            </span>
          )}
        </button>
        {!collapsed && content && (
          <div className="px-3 py-2.5 text-xs leading-relaxed text-text-secondary border-t border-border whitespace-pre-wrap max-h-48 overflow-y-auto font-mono bg-surface">
            {content}
          </div>
        )}
      </div>
    </div>
  );
}
