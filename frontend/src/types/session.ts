export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface FileInfo {
  url: string;
  name: string;
  size: number;
  type: 'image' | 'pdf' | 'document' | 'text';
}

export interface SearchSource {
  index: number;
  title: string;
  url: string;
}

export interface Message {
  id: number;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  status?: 'completed' | 'interrupted' | 'failed';
  timestamp: string;
  file_info?: FileInfo;
  search_sources?: SearchSource[];
}

export interface SessionListResponse {
  sessions: Session[];
}

export interface MessageListResponse {
  messages: Message[];
}
