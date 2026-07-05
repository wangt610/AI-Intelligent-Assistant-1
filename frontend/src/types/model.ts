export interface ModelItem {
  id: string;
  name: string;
  source: string;
  type: string;
}

export interface ModelListResponse {
  models: ModelItem[];
  error?: string;
}

export interface ModelSource {
  name: string;
  label: string;
  type: string;
  base_url: string;
  api_key: string;
}

export interface ModelSourceCreate {
  name: string;
  label: string;
  base_url: string;
  api_key: string;
}

export interface ModelSourceListResponse {
  sources: ModelSource[];
}
