interface Props {
  file: File;
  onRemove: () => void;
}

export function FileAttachmentUpload({ file, onRemove }: Props) {
  const isImage = file.type.startsWith('image/');
  const url = isImage ? URL.createObjectURL(file) : null;

  return (
    <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2 shadow-sm max-w-xs">
      {isImage && url ? (
        <img src={url} alt={file.name} className="w-8 h-8 rounded object-cover flex-shrink-0" />
      ) : (
        <div className="w-8 h-8 rounded bg-accent-subtle flex items-center justify-center flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-accent">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-text truncate">{file.name}</p>
        <p className="text-[10px] text-text-muted">{formatSize(file.size)}</p>
      </div>
      <button onClick={onRemove} className="btn-ghost p-1 flex-shrink-0" title="移除">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
