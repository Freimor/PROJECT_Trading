import type { OllamaStatus } from "../types";

export function isOllamaHealthy(ollama?: OllamaStatus | null): boolean {
  if (!ollama) return false;
  return ollama.status === "ok" && !ollama.error;
}

/** Status bar border: ok = green, warn = amber, error = pink (unreachable / misconfigured). */
export function ollamaStripClass(ollama?: OllamaStatus | null): "ok" | "warn" | "error" {
  if (!ollama) return "error";
  if (isOllamaHealthy(ollama)) return "ok";
  if (ollama.status === "warn") return "warn";
  return "error";
}
