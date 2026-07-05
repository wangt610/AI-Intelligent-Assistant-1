import { useEffect, useCallback } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useUIStore } from '../../stores/uiStore';
import { useClickOutside } from '../../hooks/useClickOutside';
import { fetchModels, fetchModelSources, fetchSearchStatus, warmupModel } from '../../services/models';

export function ModelPicker() {
  const models = useChatStore((s) => s.models);
  const modelSources = useChatStore((s) => s.modelSources);
  const selectedModelId = useChatStore((s) => s.selectedModelId);
  const selectedModelSource = useChatStore((s) => s.selectedModelSource);
  const warmLoading = useChatStore((s) => s.warmLoading);
  const setModels = useChatStore((s) => s.setModels);
  const setModelSources = useChatStore((s) => s.setModelSources);
  const setSelectedModel = useChatStore((s) => s.setSelectedModel);
  const setSearchAvailable = useChatStore((s) => s.setSearchAvailable);
  const setWarmLoading = useChatStore((s) => s.setWarmLoading);
  const modelDropdownOpen = useUIStore((s) => s.modelDropdownOpen);
  const setModelDropdownOpen = useUIStore((s) => s.setModelDropdownOpen);
  const addToast = useUIStore((s) => s.addToast);

  const ref = useClickOutside(useCallback(() => setModelDropdownOpen(false), [setModelDropdownOpen]));

  useEffect(() => {
    fetchModels().then((ms) => {
      setModels(ms);
      if (!selectedModelId && ms.length > 0) {
        setSelectedModel(ms[0].id, ms[0].source);
      }
    }).catch(() => {});
    fetchModelSources().then(setModelSources).catch(() => {});
    fetchSearchStatus().then((r) => setSearchAvailable(r.configured)).catch(() => {});
  }, []);

  const handleWarmup = async () => {
    setWarmLoading(true);
    const ok = await warmupModel(selectedModelId);
    addToast(ok ? '模型预热完成' : '预热失败，请检查模型是否可用', ok ? 'success' : 'error');
    setWarmLoading(false);
  };

  const grouped = models.reduce<Record<string, typeof models>>((acc, m) => {
    (acc[m.source] ||= []).push(m);
    return acc;
  }, {});

  const selectedModel = models.find((m) => m.id === selectedModelId && m.source === selectedModelSource);
  const displayName = selectedModel?.name || selectedModelSource || '选择模型';

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
        className="btn-ghost text-xs"
        title="切换模型"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
        <span className="max-w-24 truncate font-label">{displayName}</span>
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M1 1l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {modelDropdownOpen && (
        <div className="absolute bottom-full mb-1 right-0 z-30 w-64 bg-surface-elevated rounded-lg shadow-lg border border-border overflow-y-auto animate-fade-in">
          {Object.entries(grouped).length === 0 && (
            <div className="px-3 py-4 text-xs text-text-muted text-center font-label">加载中...</div>
          )}
          {Object.entries(grouped).map(([source, ms]) => {
            const sourceLabel = modelSources.find((s) => s.name === source)?.label || source;
            return (
              <div key={source}>
                <div className="px-3 py-1.5 text-xs font-label font-medium text-text-muted bg-surface-hover border-b border-border">
                  {sourceLabel}
                </div>
                {ms.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setSelectedModel(m.id, m.source);
                      setModelDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs font-label transition-colors ${
                      selectedModelId === m.id && selectedModelSource === m.source
                        ? 'bg-accent-subtle text-accent font-medium'
                        : 'text-text-secondary hover:bg-surface-hover hover:text-text'
                    }`}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
            );
          })}
          <div className="border-t border-border px-2 py-1.5">
            <button
              onClick={handleWarmup}
              disabled={warmLoading}
              className="w-full px-2 py-1.5 text-xs font-label rounded-lg bg-surface text-text-muted hover:text-text border border-border hover:border-border-hover disabled:opacity-50 transition-all"
            >
              {warmLoading ? '预热中...' : '预热模型'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
