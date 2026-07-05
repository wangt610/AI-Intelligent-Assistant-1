import { useState, useEffect, type FormEvent } from 'react';
import { useUIStore } from '../../stores/uiStore';
import { useChatStore } from '../../stores/chatStore';
import { useThemeStore } from '../../stores/themeStore';
import { addModelSource, removeModelSource, refreshModels } from '../../services/models';
import { getSettings, updateSettings, type RuntimeSettings } from '../../services/settings';

const DEFAULT_SETTINGS: RuntimeSettings = {
  temperature: 0.7,
  top_p: 0.9,
  max_context_tokens: 18000,
  max_history_messages: 40,
  max_output_tokens: 8192,
  rag_enabled: true,
  rag_chunk_size: 800,
  rag_chunk_overlap: 200,
  rag_top_k: 3,
  rag_score_threshold: 0.35,
  rag_query_rewrite: true,
  rag_hyde_enabled: true,
  rag_hyde_max_tokens: 150,
  rag_candidate_k: 20,
  rag_bm25_weight: 0.4,
  search_max_results: 5,
  search_max_context_tokens: 4000,
};

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange} className={`w-9 h-5 rounded transition-colors ${checked ? 'bg-accent' : 'bg-border'}`}>
      <div className={`w-3.5 h-3.5 rounded bg-bg shadow-sm transition-transform ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
    </button>
  );
}

function NumberInput({ value, onChange, className = '' }: { value: number; onChange: (v: number) => void; className?: string }) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(parseInt(e.target.value) || 0)}
      className={`w-20 px-2 py-1 text-xs rounded border border-border bg-surface text-text outline-none focus:border-accent focus:ring-1 focus:ring-accent/20 ${className}`}
    />
  );
}

export function SettingsModal() {
  const open = useUIStore((s) => s.settingsOpen);
  const setOpen = useUIStore((s) => s.setSettingsOpen);
  const addToast = useUIStore((s) => s.addToast);
  const models = useChatStore((s) => s.models);
  const modelSources = useChatStore((s) => s.modelSources);
  const setModels = useChatStore((s) => s.setModels);
  const setModelSources = useChatStore((s) => s.setModelSources);
  const selectedModelId = useChatStore((s) => s.selectedModelId);
  const selectedModelSource = useChatStore((s) => s.selectedModelSource);
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);

  const [tab, setTab] = useState('general');
  const [sources, setSources] = useState<typeof modelSources>([]);
  const [name, setName] = useState('');
  const [label, setLabel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);

  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings>(DEFAULT_SETTINGS);
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsChanged, setSettingsChanged] = useState(false);

  useEffect(() => {
    if (open) {
      // Use model sources from store instead of re-fetching
      setSources(modelSources);

      setLoadingSettings(true);
      getSettings()
        .then((data) => {
          setRuntimeSettings(data);
          setSettingsChanged(false);
        })
        .catch(() => addToast('加载配置失败，请检查后端服务', 'error'))
        .finally(() => setLoadingSettings(false));
    }
  }, [open, addToast]);

  const handleAddSource = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !baseUrl.trim()) {
      addToast('名称和 API 地址不能为空', 'error');
      return;
    }
    if (!apiKey.trim()) {
      addToast('API 密钥不能为空', 'error');
      return;
    }
    try {
      const updated = await addModelSource({ name: name.trim(), label: label.trim() || name.trim(), base_url: baseUrl.trim(), api_key: apiKey.trim() });
      setSources(updated);
      setModelSources(updated.map((s: { api_key: string; name: string; label: string; type: string; base_url: string }) => ({ ...s, api_key: s.api_key })));
      setName(''); setLabel(''); setBaseUrl(''); setApiKey('');
      addToast('来源已添加', 'success');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '添加失败', 'error');
    }
  };

  const handleRemoveSource = async (n: string) => {
    if (!confirm(`确定删除来源 "${n}"？`)) return;
    try {
      const updated = await removeModelSource(n);
      setSources(updated);
      addToast('来源已删除', 'success');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '删除失败', 'error');
    }
  };

  const handleRefresh = async () => {
    try {
      const ms = await refreshModels();
      setModels(ms);
      addToast('模型列表已刷新', 'success');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : '刷新失败', 'error');
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const data = await updateSettings(runtimeSettings);
      setRuntimeSettings(data);
      setSettingsChanged(false);
      addToast('配置已保存', 'success');
    } catch {
      addToast('保存配置失败', 'error');
    } finally {
      setSavingSettings(false);
    }
  };

  const updateSetting = <K extends keyof RuntimeSettings>(key: K, value: RuntimeSettings[K]) => {
    setRuntimeSettings((prev) => ({ ...prev, [key]: value }));
    setSettingsChanged(true);
  };

  const selected = models.find((m) => m.id === selectedModelId && m.source === selectedModelSource);
  const selectedSourceLabel = modelSources.find((s) => s.name === selectedModelSource)?.label || selectedModelSource;
  const themeName = theme === 'dark' ? '深色模式' : '浅色模式';

  if (!open) return null;

  const tabs = [
    { key: 'general', label: '通用' },
    { key: 'advanced', label: '高级' },
    { key: 'sources', label: '模型来源' },
    { key: 'about', label: '关于' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative bg-surface-elevated rounded shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col border border-border animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <h3 className="font-heading font-semibold text-sm text-text">设置</h3>
          <button onClick={() => setOpen(false)} className="btn-icon" title="关闭">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Sidebar */}
          <nav className="w-28 flex-shrink-0 border-r border-border p-1.5 space-y-0.5">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`w-full text-left px-2.5 py-1.5 rounded text-xs font-label transition-all ${
                  tab === t.key
                    ? 'bg-accent-subtle text-accent'
                    : 'text-text-muted hover:bg-surface-hover hover:text-text'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {/* General */}
            {tab === 'general' && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-xs font-label font-medium text-text-muted mb-2">当前模型</h4>
                  <div className="px-3 py-2.5 rounded bg-surface border border-border">
                    <div className="text-sm text-text font-medium">{selected?.name || '—'}</div>
                    <div className="text-xs text-text-muted mt-0.5">{selectedSourceLabel}</div>
                  </div>
                </div>
                <div>
                  <h4 className="text-xs font-label font-medium text-text-muted mb-2">主题</h4>
                  <div className="flex items-center justify-between px-3 py-2.5 rounded bg-surface border border-border">
                    <span className="text-sm text-text">{themeName}</span>
                    <button onClick={toggleTheme} className="btn-primary text-xs">
                      切换
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Advanced */}
            {tab === 'advanced' && (
              <div className="space-y-4">
                {loadingSettings ? (
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                    加载配置中...
                  </div>
                ) : (
                  <>
                    {/* Inference */}
                    <div>
                      <h4 className="text-xs font-label font-medium text-text-muted mb-2.5">推理参数</h4>
                      <div className="space-y-2">
                        {[
                          { label: 'Temperature', key: 'temperature' as const, step: 0.1, min: 0, max: 1 },
                          { label: 'Top P', key: 'top_p' as const, step: 0.1, min: 0, max: 1 },
                          { label: '最大输出 Token', key: 'max_output_tokens' as const },
                          { label: '上下文 Token 预算', key: 'max_context_tokens' as const },
                          { label: '历史消息数', key: 'max_history_messages' as const },
                        ].map((item) => (
                          <div key={item.key} className="flex items-center justify-between">
                            <span className="text-xs text-text">{item.label}</span>
                            <input
                              type="number"
                              step={item.step || 1}
                              min={item.min ?? 1}
                              max={item.max}
                              value={runtimeSettings[item.key] as number}
                              onChange={(e) => updateSetting(item.key, parseFloat(e.target.value) || 0)}
                              className="w-24 px-2 py-1 text-xs rounded border border-border bg-surface text-text outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
                            />
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* RAG */}
                    <div className="border-t border-border pt-4">
                      <h4 className="text-xs font-label font-medium text-text-muted mb-2.5">RAG 检索</h4>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">启用 RAG</span>
                          <Toggle checked={runtimeSettings.rag_enabled} onChange={() => updateSetting('rag_enabled', !runtimeSettings.rag_enabled)} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">分块大小</span>
                          <NumberInput value={runtimeSettings.rag_chunk_size} onChange={(v) => updateSetting('rag_chunk_size', v)} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">分块重叠</span>
                          <NumberInput value={runtimeSettings.rag_chunk_overlap} onChange={(v) => updateSetting('rag_chunk_overlap', v)} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">返回结果数</span>
                          <NumberInput value={runtimeSettings.rag_top_k} onChange={(v) => updateSetting('rag_top_k', v)} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">相似度阈值</span>
                          <input
                            type="number" step="0.05" min="0" max="1"
                            value={runtimeSettings.rag_score_threshold}
                            onChange={(e) => updateSetting('rag_score_threshold', parseFloat(e.target.value))}
                            className="w-20 px-2 py-1 text-xs rounded border border-border bg-surface text-text outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">查询重写</span>
                          <Toggle checked={runtimeSettings.rag_query_rewrite} onChange={() => updateSetting('rag_query_rewrite', !runtimeSettings.rag_query_rewrite)} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">HyDE</span>
                          <Toggle checked={runtimeSettings.rag_hyde_enabled} onChange={() => updateSetting('rag_hyde_enabled', !runtimeSettings.rag_hyde_enabled)} />
                        </div>
                      </div>
                    </div>

                    {/* Search */}
                    <div className="border-t border-border pt-4">
                      <h4 className="text-xs font-label font-medium text-text-muted mb-2.5">联网搜索</h4>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">最大结果数</span>
                          <NumberInput value={runtimeSettings.search_max_results} onChange={(v) => updateSetting('search_max_results', v)} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text">上下文 Token</span>
                          <NumberInput value={runtimeSettings.search_max_context_tokens} onChange={(v) => updateSetting('search_max_context_tokens', v)} className="w-24" />
                        </div>
                      </div>
                    </div>

                    {/* Save */}
                    <div className="border-t border-border pt-4 flex items-center gap-3">
                      <button
                        onClick={handleSaveSettings}
                        disabled={savingSettings || !settingsChanged}
                        className={`px-4 py-2 rounded text-xs font-label font-medium transition-all ${
                          settingsChanged
                            ? 'btn-primary'
                            : 'bg-surface text-text-dim cursor-not-allowed border border-border'
                        }`}
                      >
                        {savingSettings ? '保存中...' : '保存配置'}
                      </button>
                      {settingsChanged && (
                        <span className="text-xs text-warning font-label">未保存的更改</span>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Sources */}
            {tab === 'sources' && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-xs font-label font-medium text-text-muted mb-2">已添加的来源</h4>
                  {sources.length === 0 ? (
                    <div className="text-xs text-text-muted py-2">暂无自定义来源</div>
                  ) : (
                    <div className="space-y-1.5">
                      {sources.map((s) => (
                        <div key={s.name} className="flex items-center justify-between px-3 py-2 rounded bg-surface border border-border text-xs">
                          <div>
                            <div className="font-label font-medium text-text">{s.label}</div>
                            <div className="text-text-muted font-mono text-[10px] mt-0.5">{s.base_url}</div>
                          </div>
                          <button
                            onClick={() => handleRemoveSource(s.name)}
                            className="btn-icon text-text-muted hover:text-error"
                            title="删除"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="border-t border-border pt-4">
                  <h4 className="text-xs font-label font-medium text-text-muted mb-2">添加新来源</h4>
                  <form onSubmit={handleAddSource} className="space-y-2">
                    <input value={name} onChange={(e) => setName(e.target.value)} placeholder="名称" className="input-field text-xs" />
                    <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="显示名称" className="input-field text-xs" />
                    <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="API 地址" className="input-field text-xs" />
                    <div className="flex gap-2">
                      <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type={showKey ? 'text' : 'password'} placeholder="API 密钥" className="flex-1 input-field text-xs" />
                      <button type="button" onClick={() => setShowKey(!showKey)} className="btn-icon" title={showKey ? '隐藏' : '显示'}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      </button>
                    </div>
                    <div className="flex gap-2 pt-1">
                      <button type="submit" className="btn-primary text-xs">添加来源</button>
                      <button type="button" onClick={handleRefresh} className="btn-ghost text-xs">刷新模型</button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* About */}
            {tab === 'about' && (
              <div className="space-y-4">
                <div className="px-4 py-3 rounded bg-surface border border-border">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="w-7 h-7 rounded flex items-center justify-center bg-accent/10">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                      </svg>
                    </div>
                    <div>
                      <div className="font-heading font-semibold text-sm text-text">AI 智能助手</div>
                      <div className="text-xs text-text-muted font-label">v2.0.0</div>
                    </div>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between"><span className="text-text-muted">引擎</span><span className="text-text">Ollama + FastAPI</span></div>
                    <div className="flex justify-between"><span className="text-text-muted">前端</span><span className="text-text">React + Tailwind</span></div>
                    <div className="flex justify-between"><span className="text-text-muted">流式协议</span><span className="text-text font-mono">SSE</span></div>
                    <div className="flex justify-between"><span className="text-text-muted">API 端点</span><span className="text-text font-mono">/api/chat</span></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
