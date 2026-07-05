import { apiFetch } from './api';

export interface RuntimeSettings {
  temperature: number;
  top_p: number;
  max_context_tokens: number;
  max_history_messages: number;
  max_output_tokens: number;
  rag_enabled: boolean;
  rag_chunk_size: number;
  rag_chunk_overlap: number;
  rag_top_k: number;
  rag_score_threshold: number;
  rag_query_rewrite: boolean;
  rag_hyde_enabled: boolean;
  rag_hyde_max_tokens: number;
  rag_candidate_k: number;
  rag_bm25_weight: number;
  search_max_results: number;
  search_max_context_tokens: number;
}

export async function getSettings(): Promise<RuntimeSettings> {
  return apiFetch<RuntimeSettings>('/settings');
}

export async function updateSettings(settings: RuntimeSettings): Promise<RuntimeSettings> {
  return apiFetch<RuntimeSettings>('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}
