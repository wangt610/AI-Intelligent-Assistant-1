import { apiFetch } from './api';
import type { Session, Message, SessionListResponse, MessageListResponse } from '../types/session';

export async function fetchSessions(): Promise<Session[]> {
  const data = await apiFetch<SessionListResponse>('/sessions');
  return data.sessions;
}

export async function searchSessions(q: string): Promise<Session[]> {
  const data = await apiFetch<SessionListResponse>(`/sessions/search?q=${encodeURIComponent(q)}`);
  return data.sessions;
}

export async function createSession(title = '新对话'): Promise<Session> {
  return apiFetch<Session>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function renameSession(id: string, title: string): Promise<void> {
  await apiFetch(`/sessions/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  });
}

export async function deleteSession(id: string): Promise<void> {
  await apiFetch(`/sessions/${id}`, { method: 'DELETE' });
}

export async function fetchMessages(sessionId: string): Promise<Message[]> {
  const data = await apiFetch<MessageListResponse>(`/sessions/${sessionId}/messages`);
  return data.messages;
}

export async function editMessage(
  sessionId: string,
  messageId: number,
  content: string,
): Promise<void> {
  await apiFetch(`/sessions/${sessionId}/messages/${messageId}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

export async function deleteMessage(
  sessionId: string,
  messageId: number,
): Promise<void> {
  await apiFetch(`/sessions/${sessionId}/messages/${messageId}`, {
    method: 'DELETE',
  });
}
