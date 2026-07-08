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

function operatorHeaders(password?: string): HeadersInit {
  const pwd = password ?? getOperatorPassword();
  const legacy = localStorage.getItem("adminKey");
  const h: Record<string, string> = {};
  if (pwd) h["X-Operator-Password"] = pwd;
  if (legacy) h["X-Admin-Key"] = legacy;
  return h;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableError(err: unknown): boolean {
  if (err instanceof TypeError) return true;
  if (err instanceof Error) {
    return err.name === "AbortError" || err.message.startsWith("HTTP ");
  }
  return false;
}

async function parseResponse<T>(res: Response, path: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status} (${path}): ${text.slice(0, 200)}`);
  }
  return res.json();
}

async function fetchOnce<T>(
  path: string,
  options: {
    timeoutMs: number;
    method?: "GET" | "POST";
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
    if (options.method === "POST") {
      init.method = "POST";
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
  const retries = options?.retries ?? 3;
  let lastError: unknown;
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      return await fetchOnce<T>(path, { timeoutMs });
    } catch (err) {
      lastError = err;
      if (!isRetryableError(err) || attempt === retries - 1) break;
      await sleep(400 * (attempt + 1));
    }
  }
  throw lastError;
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: { timeoutMs?: number; retries?: number; operatorPassword?: string },
): Promise<T> {
  const timeoutMs = options?.timeoutMs ?? 300_000;
  const retries = options?.retries ?? 2;
  let lastError: unknown;
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      return await fetchOnce<T>(path, {
        timeoutMs,
        method: "POST",
        body,
        operatorPassword: options?.operatorPassword,
      });
    } catch (err) {
      lastError = err;
      if (!isRetryableError(err) || attempt === retries - 1) break;
      await sleep(500 * (attempt + 1));
    }
  }
  throw lastError;
}
