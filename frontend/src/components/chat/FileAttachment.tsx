import { useState } from 'react';
import type { FileInfo } from '../../types/session';
import { FilePreview } from './FilePreview';

interface Props {
  info: FileInfo;
}

const FILE_ICONS: Record<string, React.ReactNode> = {
  image: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>
    </svg>
  ),
  pdf: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <path d="M9 15h6"/><path d="M12 12v6"/>
    </svg>
  ),
  document: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  text: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/>
    </svg>
  ),
};

export function FileAttachment({ info }: Props) {
  const [previewOpen, setPreviewOpen] = useState(false);

  if (info.type === 'image') {
    return (
      <>
        <button onClick={() => setPreviewOpen(true)} className="block max-w-[180px] max-h-[180px] rounded-lg overflow-hidden border border-border hover:opacity-90 transition-opacity">
          <img src={info.url} alt={info.name} className="w-full h-full object-contain" loading="lazy" />
        </button>
        {previewOpen && <FilePreview info={info} onClose={() => setPreviewOpen(false)} />}
      </>
    );
  }

  const icon = FILE_ICONS[info.type] || FILE_ICONS.document;

  return (
    <a
      href={info.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-3 bg-surface border border-border rounded-lg px-4 py-3 hover:bg-accent-subtle/30 transition-colors max-w-sm"
    >
      <div className="text-accent">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text truncate">{info.name}</p>
        <p className="text-[11px] text-text-muted">{formatSize(info.size)}</p>
      </div>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-text-muted flex-shrink-0">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
      </svg>
    </a>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
