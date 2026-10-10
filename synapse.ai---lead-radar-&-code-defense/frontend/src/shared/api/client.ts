/**
 * Minimal JSON API client shared by every module's `api.ts`.
 * Infrastructure only: no endpoint paths or module knowledge belongs here.
 */

/** Structured error body returned by the backend for every non-2xx response. */
export interface ApiErrorBody {
  detail: string;
  code: string;
  errors?: Array<{ field: string; message: string }>;
}

export class ApiError extends Error {
  readonly status: number;
  /** Machine-readable code from the backend (e.g. "ai_unavailable"), or "network_error". */
  readonly code: string;
  readonly fieldErrors: Array<{ field: string; message: string }>;

  constructor(message: string, status: number, code = 'error', fieldErrors: ApiErrorBody['errors'] = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors ?? [];
  }
}

// Same-origin by default (Vite proxies /api to FastAPI). Override only for cross-origin deployments.
const API_BASE: string = (((import.meta as any).env?.VITE_API_BASE_URL as string | undefined) ?? '').replace(/\/$/, '');

interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  /** Message used when the server gives no readable `detail` in its error body. */
  errorMessage: string;
}

export async function requestJson<T>(path: string, options: RequestOptions): Promise<T> {
  const { method = 'GET', body, errorMessage } = options;
  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    // Network failure: surface it. Callers must never substitute made-up data.
    throw new ApiError('The server could not be reached. Check that the backend is running.', 0, 'network_error');
  }

  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as Partial<ApiErrorBody> | null;
    let message = typeof err?.detail === 'string' && err.detail ? err.detail : errorMessage;
    const first = err?.errors?.[0];
    if (first) message += ` (${first.field}: ${first.message.replace(/^Value error, /, '')})`;
    throw new ApiError(message, res.status, err?.code ?? 'error', err?.errors);
  }
  return res.json() as Promise<T>;
}
