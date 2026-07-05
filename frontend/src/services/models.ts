import { apiFetch } from './api';
import type { ModelItem, ModelListResponse, ModelSource, ModelSourceCreate, ModelSourceListResponse } from '../types/model';

export async function fetchModels(): Promise<ModelItem[]> {
  const data = await apiFetch<ModelListResponse>('/models');
  return data.models;
}

export async function refreshModels(): Promise<ModelItem[]> {
  const data = await apiFetch<ModelListResponse>('/models/refresh', { method: 'POST' });
  return data.models;
}

export async function fetchModelSources(): Promise<ModelSource[]> {
  const data = await apiFetch<ModelSourceListResponse>('/model-sources');
  return data.sources;
}

export async function addModelSource(source: ModelSourceCreate): Promise<ModelSource[]> {
  const data = await apiFetch<ModelSourceListResponse>('/model-sources', {
    method: 'POST',
    body: JSON.stringify(source),
  });
  return data.sources;
}

export async function removeModelSource(name: string): Promise<ModelSource[]> {
  const data = await apiFetch<ModelSourceListResponse>(`/model-sources/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
  return data.sources;
}

export async function warmupModel(model_id?: string): Promise<boolean> {
  const params = model_id ? `?model_id=${encodeURIComponent(model_id)}` : '';
  const data = await apiFetch<{ ok: boolean }>(`/models/warm${params}`, { method: 'POST' });
  return data.ok;
}

export async function fetchSearchStatus(): Promise<{ configured: boolean }> {
  return apiFetch<{ configured: boolean }>('/search/status');
}
