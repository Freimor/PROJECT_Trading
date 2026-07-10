type TranslateFn = (key: string, vars?: Record<string, string | number>) => string;

export const OPERATOR_PASSWORD_ERROR_CODE = "OPERATOR_PASSWORD_INVALID";

export class OperatorPasswordError extends Error {
  readonly code = OPERATOR_PASSWORD_ERROR_CODE;

  constructor() {
    super(OPERATOR_PASSWORD_ERROR_CODE);
    this.name = "OperatorPasswordError";
  }
}

export function isOperatorPasswordError(err: unknown): boolean {
  if (err instanceof OperatorPasswordError) return true;
  if (!(err instanceof Error)) return false;
  const msg = err.message.toLowerCase();
  return (
    err.name === "OperatorPasswordError" ||
    msg === OPERATOR_PASSWORD_ERROR_CODE.toLowerCase() ||
    msg.includes("invalid operator password") ||
    msg.includes("operator_password_invalid") ||
    msg.includes("http 401")
  );
}

/** User-facing text for operator modal errors (password, network, HTTP). */
export function formatOperatorFacingError(err: unknown, t: TranslateFn): string {
  if (isOperatorPasswordError(err)) {
    return t("workspace.wrongOperatorPassword");
  }
  if (err instanceof Error) {
    const msg = err.message.replace(/^Error:\s*/i, "");
    if (msg.startsWith("Сеть недоступна")) {
      return t("workspace.networkError");
    }
    return msg;
  }
  return String(err ?? "unknown_error");
}
