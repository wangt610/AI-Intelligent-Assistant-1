import { useRef, useState, useEffect, type KeyboardEvent } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useSessionStore } from '../../stores/sessionStore';
import { useVoiceInput } from '../../hooks/useVoiceInput';
import { useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { ModelPicker } from './ModelPicker';
import { FileAttachmentUpload } from './FileAttachmentUpload';

export function InputArea() {
  const input = useChatStore((s) => s.input);
  const setInput = useChatStore((s) => s.setInput);
  const streaming = useChatStore((s) => s.streaming);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const sendFileMessage = useChatStore((s) => s.sendFileMessage);
  const stopStreaming = useChatStore((s) => s.stopStreaming);
  const webSearchEnabled = useChatStore((s) => s.webSearchEnabled);
  const toggleWebSearch = useChatStore((s) => s.toggleWebSearch);
  const currentRagMode = useChatStore((s) => s.currentRagMode);
  const toggleRagMode = useChatStore((s) => s.toggleRagMode);
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { loadDraft, clearDraft } = useDraftAutoSave(currentSessionId, input);

  useEffect(() => {
    if (currentSessionId) {
      const draft = loadDraft(currentSessionId);
      setInput(draft);
    } else {
      setInput('');
    }
  }, [currentSessionId]);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    if (!currentSessionId || streaming) return;
    if (pendingFile) {
      doFileUpload(pendingFile);
      return;
    }
    if (!input.trim()) return;
    const msg = input.trim();
    clearDraft(currentSessionId);
    setInput('');
    sendMessage(currentSessionId, msg);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceResult = (text: string) => {
    setInput(useChatStore.getState().input + text);
  };

  const { listening, start: startVoice, stop: stopVoice } = useVoiceInput(handleVoiceResult);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingFile(file);
    e.target.value = '';
  };

  const doFileUpload = (file: File) => {
    if (!currentSessionId) return;
    const msgText = input || '请分析这个文件';
    setInput('');
    setPendingFile(null);
    clearDraft(currentSessionId);
    sendFileMessage(currentSessionId, msgText, file);
  };

  const canSend = Boolean(currentSessionId && (input.trim() || pendingFile));

  return (
    <div className="border-t border-border bg-surface shrink-0">
      <div className="max-w-5xl mx-auto px-4 py-3">
        {/* Pending file chip */}
        {pendingFile && (
          <div className="mb-2">
            <FileAttachmentUpload file={pendingFile} onRemove={() => setPendingFile(null)} />
          </div>
        )}

        {/* Input bar */}
        <div className="flex items-center gap-1.5 mb-2">
          <label
            className="btn-ghost text-xs cursor-pointer"
            title="上传文件"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            上传
            <input ref={fileInputRef} type="file" accept=".txt,.pdf,.docx,.xlsx,.md,.jpg,.jpeg,.png,.gif,.webp" hidden onChange={handleFileSelect} />
          </label>

          <button
            onClick={listening ? stopVoice : startVoice}
            className={`btn-ghost text-xs ${listening ? 'text-error active' : ''}`}
            title={listening ? '停止录音' : '语音输入'}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
            {listening ? '录音中' : '语音'}
          </button>

          <button
            onClick={toggleWebSearch}
            className={`btn-ghost text-xs ${webSearchEnabled ? 'active' : ''}`}
            title="联网搜索"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            联网
          </button>

          <button
            onClick={toggleRagMode}
            className={`btn-ghost text-xs ${currentRagMode !== 'off' ? 'active' : ''}`}
            title={`知识库: ${currentRagMode === 'off' ? '关闭' : currentRagMode === 'auto' ? '自动' : '强制'}`}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
            {currentRagMode === 'off' ? '知识库' : currentRagMode === 'auto' ? '自动' : '强制'}
          </button>

          <div className="flex-1" />

          <ModelPicker />
        </div>

        {/* Textarea + send */}
        <div className="flex items-end gap-2">
          <textarea
            id="messageInput"
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={currentSessionId ? (pendingFile ? '添加描述（可选）...' : '输入消息...') : '请先选择或创建一个对话'}
            disabled={!currentSessionId}
            rows={1}
            className="flex-1 bg-surface text-sm text-text placeholder:text-text-muted resize-none outline-none border border-border rounded-lg px-3 py-2.5 focus:border-accent focus:ring-2 focus:ring-accent/15 disabled:opacity-50 shadow-sm"
          />

          {streaming ? (
            <button
              onClick={stopStreaming}
              className="btn-primary text-xs bg-error hover:bg-error/90"
              title="停止生成"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"/>
              </svg>
              停止
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!canSend}
              className="btn-primary text-xs"
              title="发送 (Enter)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
