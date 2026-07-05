export interface ChatRequest {
  session_id: string;
  message: string;
  show_thinking: boolean;
  rag_mode: 'off' | 'auto' | 'force';
  web_search: boolean;
  model_source?: string;
  model_id?: string;
}

export interface RegenerateRequest {
  session_id: string;
  show_thinking: boolean;
  rag_mode: 'off' | 'auto' | 'force';
  web_search: boolean;
  model_source?: string;
  model_id?: string;
}

export interface RAGSource {
  file: string;
  score: number;
  type: string;
}
