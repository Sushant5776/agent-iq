import { NextResponse } from "next/server";

import { readApiPayload } from "./http";

export const MAX_MULTIPART_BODY_BYTES = 4 * 1024 * 1024 + 256 * 1024;

function textValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

export function proxyError(
  status: number,
  code: string,
  detail: string,
  requestId: string,
) {
  return NextResponse.json(
    { code, detail, request_id: requestId },
    { status, headers: { "X-Request-ID": requestId } },
  );
}

export async function proxyAgentIq(
  path: string,
  init: RequestInit,
  requestId = crypto.randomUUID(),
) {
  const baseUrl = process.env.AGENTIQ_API_BASE_URL;
  const token = process.env.AGENTIQ_API_ACCESS_TOKEN;
  if (!baseUrl || !token) {
    return proxyError(
      503,
      "api_not_configured",
      "AgentIQ API is not configured",
      requestId,
    );
  }

  try {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${token}`);
    headers.set("X-Request-ID", requestId);
    const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
    const payload = await readApiPayload(response);
    const resolvedRequestId =
      textValue(payload.request_id) ||
      response.headers.get("X-Request-ID") ||
      requestId;

    if (response.ok && Object.keys(payload).length === 0) {
      return proxyError(
        502,
        "invalid_upstream_response",
        "AgentIQ API returned an empty or invalid response",
        resolvedRequestId,
      );
    }

    const output = response.ok
      ? { ...payload, request_id: resolvedRequestId }
      : {
          code: textValue(payload.code) || `http_${response.status}`,
          detail:
            textValue(payload.detail) ||
            `AgentIQ API request failed with HTTP ${response.status}`,
          request_id: resolvedRequestId,
        };
    return NextResponse.json(output, {
      status: response.status,
      headers: { "X-Request-ID": resolvedRequestId },
    });
  } catch {
    return proxyError(
      502,
      "api_unavailable",
      "AgentIQ API is unavailable",
      requestId,
    );
  }
}
