import { useState, useEffect, useRef } from 'react';
import hljs from 'highlight.js';

interface Props {
  code: string;
  lang?: string;
}

export function CodeBlock({ code, lang }: Props) {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (codeRef.current) {
      hljs.highlightElement(codeRef.current);
    }
  }, [code, lang]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  return (
    <div className="relative group my-3 rounded-lg overflow-hidden border border-border shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-elevated text-xs font-label text-text-muted border-b border-border">
        <span className="text-accent">{lang || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 rounded text-text-muted hover:text-text hover:bg-surface-hover transition-all"
        >
          {copied ? (
            <>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              <span className="text-accent">已复制</span>
            </>
          ) : (
            <>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              复制
            </>
          )}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-sm leading-relaxed bg-surface">
        <code ref={codeRef} className={lang ? `language-${lang}` : ''}>{code}</code>
      </pre>
    </div>
  );
}
