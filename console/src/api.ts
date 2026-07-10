import { OperatorPasswordError } from "./apiErrors";

const API = import.meta.env.VITE_API_URL || "";

const RETRYABLE_HTTP = new Set([408, 429, 502, 503, 504]);

export const OPERATOR_PASSWORD_KEY = "operatorPassword";

export function getOperatorPassword(): string {
  return sessionStorage.getItem(OPERATOR_PASSWORD_KEY) || "";
}

export function setOperatorPassword(password: string): void {
  if (password) {
    sessionStorage.setItem(OPERATOR_PASSWORD_KEY, password);
  } else {
    sessionStorage.removeItem(OPERATOR_PASSWORD_KEY);
  }
}

function encodeOperatorPassword(password: string): string {
  const bytes = new TextEncoder().encode(password);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return `b64:${btoa(binary)}`;
}

function operatorHeaders(password?: string): HeadersInit {
  const legacy = localStorage.getItem("adminKey");
  const h: Record<string, string> = {};
  if (password) {
    if (password.length > 256 || /[\r\n\x00]/.test(password)) {
      throw new OperatorPasswordError();
    }
    h["X-Operator-Password"] = encodeOperatorPassword(password);
  }
  if (legacy) h["X-Admin-Key"] = legacy;
  return h;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableError(err: unknown): boolean {
  if (err instanceof OperatorPasswordError) return false;
  if (err instanceof TypeError) return true;
  if (err instanceof Error) {
    if (/HTTP (401|403|400|404|422) /.test(err.message)) return false;
    return err.name === "AbortError" || err.message.startsWith("HTTP ");
  }
  return false;
}

export { OperatorPasswordError, formatOperatorFacingError, isOperatorPasswordError } from "./apiErrors";

async function parseResponse<T>(res: Response, path: string): Promise<T> {
  const text = await res.text();
  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      throw new OperatorPasswordError();
    }
    throw new Error(`HTTP ${res.status} (${path}): ${text.slice(0, 200)}`);
  }
  if (!text) {
    return {} as T;
  }
  return JSON.parse(text) as T;
}

async function fetchOnce<T>(
  path: string,
  options: {
    timeoutMs: number;
    method?: "GET" | "POST" | "PUT" | "PATCH";
    body?: unknown;
    operatorPassword?: string;
  },
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs);
  try {
    const init: RequestInit = {
      signal: controller.signal,
      headers: operatorHeaders(options.operatorPassword),
    };
    if (options.method && options.method !== "GET") {
      init.method = options.method;
      init.headers = {
        "Content-Type": "application/json",
        ...operatorHeaders(options.operatorPassword),
      };
      init.body = JSON.stringify(options.body ?? {});
    }
    const res = await fetch(`${API}${path}`, init);
    if (!res.ok && RETRYABLE_HTTP.has(res.status)) {
      throw new Error(`HTTP ${res.status} (${path})`);
    }
    return await parseResponse<T>(res, path);
  } catch (err) {
    if (err instanceof OperatorPasswordError) {
      throw err;
    }
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`Таймаут запроса: ${path}`);
    }
    if (err instanceof TypeError) {
      throw new Error(`Сеть недоступна (${path}). Проверьте db-api и console.`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export async function apiGet<T>(
  path: string,
  options?: { timeoutMs?: number; retries?: number },
): Promise<T> {
  const timeoutMs = options?.timeoutMs ?? 120_000;
  const maxAttempts = options?.retries === 0 ? 1 : (options?.retries ?? 3);
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await fetchOnce<T>(path, { timeoutMs });
    } catch (err) {
      lastError = err;
      if (!isRetryableError(err) || attempt === maxAttempts - 1) break;
      await sleep(400 * (attempt + 1));
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError ?? "request_failed"));
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: { timeoutMs?: number; retries?: number; operatorPassword?: string },
): Promise<T> {
  const timeoutMs = options?.timeoutMs ?? 300_000;
  const maxAttempts = options?.retries === 0 ? 1 : (options?.retries ?? 2);
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await fetchOnce<T>(path, {
        timeoutMs,
        method: "POST",
        body,
        operatorPassword: options?.operatorPassword,
      });
    } catch (err) {
      lastError = err;
      if (!isRetryableError(err) || attempt === maxAttempts - 1) break;
      await sleep(500 * (attempt + 1));
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError ?? "request_failed"));
}

export async function apiPut<T>(
  path: string,
  body?: unknown,
  options?: { timeoutMs?: number },
): Promise<T> {
  return fetchOnce<T>(path, { timeoutMs: options?.timeoutMs ?? 60_000, method: "PUT", body });
}

export async function apiPatch<T>(
  path: string,
  body?: unknown,
  options?: { timeoutMs?: number },
): Promise<T> {
  return fetchOnce<T>(path, { timeoutMs: options?.timeoutMs ?? 60_000, method: "PATCH", body });
}
