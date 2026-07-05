const BASE = '/api';

let requestIdCounter = 0;
function nextRequestId(): string {
  requestIdCounter += 1;
  return `req_${Date.now()}_${requestIdCounter}`;
}

export class ApiError extends Error {
  public status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 30000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'X-Request-ID': nextRequestId(),
        ...(options.body instanceof FormData
          ? {}
          : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new ApiError(res.status, text || `HTTP ${res.status}`);
    }

    const text = await res.text();
    return (text ? JSON.parse(text) : null) as T;
  } finally {
    clearTimeout(timer);
  }
}

export function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: string, data: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): Promise<void> {
  return (async () => {
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (currentEvent) {
              onEvent(currentEvent, data);
              currentEvent = '';
            }
          } else if (line.startsWith('id: ')) {
            // SSE event ID — tracked by caller for reconnection
          } else if (line.startsWith('retry: ')) {
            // SSE retry hint — tracked by caller for reconnection interval
          }
        }
      }
      onDone();
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();
}

export function apiStream(
  path: string,
  body: unknown,
  onEvent: (event: string, data: string) => void,
  onError: (err: Error) => void,
  onDone: () => void,
): AbortController {
  return _apiStreamInternal(path, { body, isJson: true }, onEvent, onError, onDone);
}

export function apiStreamFormData(
  path: string,
  formData: FormData,
  onEvent: (event: string, data: string) => void,
  onError: (err: Error) => void,
  onDone: () => void,
): AbortController {
  return _apiStreamInternal(path, { body: formData, isJson: false }, onEvent, onError, onDone);
}

function _apiStreamInternal(
  path: string,
  options: { body: unknown; isJson: boolean },
  onEvent: (event: string, data: string) => void,
  onError: (err: Error) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const fetchOptions: RequestInit = {
        method: 'POST',
        signal: controller.signal,
      };
      if (options.isJson) {
        fetchOptions.headers = { 'Content-Type': 'application/json', 'X-Request-ID': nextRequestId() };
        fetchOptions.body = JSON.stringify(options.body);
      } else {
        fetchOptions.body = options.body as FormData;
      }

      const res = await fetch(`${BASE}${path}`, fetchOptions);

      if (!res.ok) {
        onError(new ApiError(res.status, `HTTP ${res.status}`));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError(new Error('No response body'));
        return;
      }

      await parseSSEStream(reader, onEvent, onDone, onError);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}
