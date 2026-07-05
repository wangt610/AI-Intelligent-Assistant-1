import { useEffect, useRef, useState } from 'react';

interface Props {
  containerRef: React.RefObject<HTMLDivElement | null>;
  children: React.ReactNode;
}

export function ScrollContainer({ containerRef, children }: Props) {
  const [showBtn, setShowBtn] = useState(false);
  const autoScrollRef = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    function onScroll() {
      if (!el) return;
      const threshold = 100;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
      autoScrollRef.current = atBottom;
      setShowBtn(!atBottom);
    }

    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, [containerRef]);

  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [containerRef, children]);

  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
      autoScrollRef.current = true;
      setShowBtn(false);
    }
  };

  return (
    <div className="relative flex-1 min-h-0">
      <div ref={containerRef} className="h-full overflow-y-auto">
        {children}
      </div>
      {showBtn && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-surface-elevated text-text-muted hover:text-text rounded p-2 shadow-lg border border-border hover:border-border-hover transition-all z-10 animate-fade-in"
          title="滚动到底部"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
      )}
    </div>
  );
}
