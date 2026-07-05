import { useRef } from 'react';
import { useSessionStore } from '../../stores/sessionStore';
import { useChatStore } from '../../stores/chatStore';
import { EmptyState } from '../ui/EmptyState';
import { ScrollContainer } from '../ui/ScrollToBottom';
import { MessageBubble } from './MessageBubble';

export function ChatArea() {
  const currentSessionId = useSessionStore((s) => s.currentSessionId);
  const messages = useSessionStore((s) => s.messages);
  const messagesLoading = useSessionStore((s) => s.messagesLoading);
  const interruptedMessage = useSessionStore((s) => s.interruptedMessage);
  const clearInterruptedMessage = useSessionStore((s) => s.clearInterruptedMessage);
  const streaming = useChatStore((s) => s.streaming);
  const thinking = useChatStore((s) => s.thinking);
  const showThinking = useChatStore((s) => s.showThinking);
  const retryInterruptedMessage = useChatStore((s) => s.retryInterruptedMessage);
  const containerRef = useRef<HTMLDivElement>(null);

  if (!currentSessionId) {
    return <EmptyState />;
  }

  if (messagesLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin"/>
          <div className="text-xs text-text-muted font-label">LOADING...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      {/* Interrupted message banner */}
      {interruptedMessage && !streaming && (
        <div className="mx-6 mt-3 mb-0 flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg bg-warning-subtle border border-warning-border">
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-warning shrink-0">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span className="text-xs text-text-secondary">
              上次回复被中断
            </span>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={() => {
                if (currentSessionId) {
                  retryInterruptedMessage(currentSessionId, interruptedMessage.userMessage);
                }
              }}
              className="btn-ghost text-xs"
            >
              重新生成
            </button>
            <button
              onClick={clearInterruptedMessage}
              className="btn-ghost text-xs"
            >
              忽略
            </button>
          </div>
        </div>
      )}

      <ScrollContainer containerRef={containerRef}>
        <div className="py-6 px-4 max-w-5xl mx-auto w-full">
          {messages.map((msg, i) => (
            <MessageBubble
              key={msg.id !== 0 && msg.id !== -1 && msg.id !== -2 ? msg.id : `temp_${i}`}
              message={msg}
              isStreaming={streaming && i === messages.length - 1 && msg.role === 'assistant'}
              thinking={i === messages.length - 1 && msg.role === 'assistant' && streaming && showThinking ? thinking : undefined}
            />
          ))}
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center text-text-muted select-none">
                <div className="text-4xl mb-3 opacity-20">💬</div>
                <p className="text-sm font-heading">发送消息开始对话</p>
              </div>
            </div>
          )}
        </div>
      </ScrollContainer>
    </div>
  );
}
