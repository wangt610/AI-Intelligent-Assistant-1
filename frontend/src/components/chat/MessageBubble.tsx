import { memo, useState } from 'react';
import type { Message } from '../../types/session';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ThinkingPanel } from './ThinkingPanel';
import { FileAttachment } from './FileAttachment';
import { useSessionStore } from '../../stores/sessionStore';
import { useChatStore } from '../../stores/chatStore';
import { useUIStore } from '../../stores/uiStore';

interface Props {
  message: Message;
  isStreaming?: boolean;
  thinking?: string;
}

export const MessageBubble = memo(function MessageBubble({ message, isStreaming, thinking }: Props) {
  const editMessage = useSessionStore((s) => s.editMessage);
  const deleteMessage = useSessionStore((s) => s.deleteMessage);
  const regenerate = useChatStore((s) => s.regenerate);
  const streaming = useChatStore((s) => s.streaming);
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  const isUser = message.role === 'user';
  const addToast = useUIStore((s) => s.addToast);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      addToast('已复制', 'success');
    } catch { /* ignore */ }
  };

  const handleEdit = async () => {
    if (editContent.trim() && editContent !== message.content) {
      await editMessage(message.id, editContent.trim());
    }
    setEditing(false);
  };

  const handleDelete = async () => {
    if (confirm('确定删除此消息及其后的所有消息？')) {
      await deleteMessage(message.id);
    }
  };

  const handleRegenerate = () => {
    if (currentSessionId && !streaming) {
      regenerate(currentSessionId);
    }
  };

  return (
    <div className={`group relative mb-8 ${isUser ? 'animate-slide-right' : 'animate-slide-left'}`}>
      {/* Thinking panel */}
      {!isUser && thinking !== undefined && (
        <ThinkingPanel content={thinking} streaming={isStreaming || false} />
      )}

      <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center shadow-sm ${
          isUser
            ? 'bg-accent text-white'
            : 'bg-surface border border-border'
        }`}>
          {isUser ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="text-accent">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          )}
        </div>

        {/* Message content */}
        <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
          {editing ? (
            <div className="w-full">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full p-3 text-sm rounded-lg bg-surface border border-accent/50 text-text outline-none resize-none focus:ring-2 focus:ring-accent/30 shadow-sm"
                rows={3}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEdit(); }
                  if (e.key === 'Escape') setEditing(false);
                }}
              />
              <div className="flex gap-2 mt-2">
                <button onClick={handleEdit} className="btn-primary text-xs">保存</button>
                <button onClick={() => setEditing(false)} className="btn-ghost text-xs">取消</button>
              </div>
            </div>
          ) : (
            <>
              <div className={`px-4 py-3 text-sm leading-relaxed ${
                isUser
                  ? 'bg-accent-subtle text-text border border-accent-border rounded-2xl rounded-tr-md dark:shadow-[0_0_12px_rgba(34,211,238,0.06)]'
                  : 'text-text'
              }`}>
                {isUser ? (
                  <div>
                    {message.file_info && (
                      <div className="mb-2">
                        <FileAttachment info={message.file_info} />
                      </div>
                    )}
                    {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}
                  </div>
                ) : (
                  <MarkdownRenderer content={message.content} searchSources={message.search_sources} />
                )}
              </div>

              {/* Action buttons - hidden during streaming, hover for assistant */}
              {!editing && !isStreaming && (
                <div className={`flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity`}>
                  <button
                    onClick={handleCopy}
                    className="btn-ghost text-[11px] py-1 px-2"
                    title="复制内容"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                    </svg>
                    复制
                  </button>
                  {isUser && (
                    <button
                      onClick={() => { setEditing(true); setEditContent(message.content); }}
                      className="btn-ghost text-[11px] py-1 px-2"
                      title="编辑消息"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                      编辑
                    </button>
                  )}
                  {!isUser && (
                    <button
                      onClick={handleRegenerate}
                      className="btn-ghost text-[11px] py-1 px-2"
                      title="重新生成回复"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                      </svg>
                      重新生成
                    </button>
                  )}
                  <button
                    onClick={handleDelete}
                    className="btn-ghost text-[11px] py-1 px-2 text-error/70 hover:text-error hover:bg-error-subtle"
                    title="删除消息"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                    删除
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
});
