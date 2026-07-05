import { useEffect } from 'react';
import type { FileInfo } from '../../types/session';

interface Props {
  info: FileInfo;
  onClose: () => void;
}

export function FilePreview({ info, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative max-w-[90vw] max-h-[90vh] flex flex-col">
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white/80 hover:text-white"
          title="关闭 (Esc)"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>

        {info.type === 'image' ? (
          <img src={info.url} alt={info.name} className="max-w-full max-h-[85vh] rounded-lg object-contain" />
        ) : (
          <div className="bg-surface border border-border rounded-lg px-6 py-8 text-center max-w-md">
            <p className="text-text mb-2">无法预览此文件类型</p>
            <a href={info.url} download className="btn-primary text-sm inline-flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载文件
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
