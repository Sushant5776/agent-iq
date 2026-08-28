export type ApiPayload = Record<string, unknown>;

export async function readApiPayload(response: Response): Promise<ApiPayload> {
  const body = await response.text();
  if (!body.trim()) return {};

  try {
    const parsed: unknown = JSON.parse(body);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as ApiPayload;
    }
  } catch {
    // Vercel and upstream proxies may return plain text or HTML error pages.
  }
  return {};
}

export function apiErrorMessage(
  response: Response,
  payload: ApiPayload,
  fallback: string,
): string {
  let message: string;
  if (response.status === 413) {
    message = "Upload rejected: HTTP 413. Choose a file no larger than 4 MiB.";
  } else if (response.status === 504) {
    message = "Ingestion timed out: HTTP 504. Try a smaller document.";
  } else if (typeof payload.detail === "string" && payload.detail.trim()) {
    message = payload.detail;
  } else {
    message = `${fallback} HTTP ${response.status}.`;
  }

  const requestId =
    typeof payload.request_id === "string"
      ? payload.request_id
      : response.headers.get("X-Request-ID");
  return requestId ? `${message} (request ${requestId})` : message;
}

export async function requireApiPayload(
  response: Response,
  fallback: string,
): Promise<ApiPayload> {
  const payload = await readApiPayload(response);
  if (!response.ok) {
    throw new Error(apiErrorMessage(response, payload, fallback));
  }
  return payload;
}
