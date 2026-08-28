import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { proxyAgentIq } from "./api-proxy";

describe("AgentIQ API proxy", () => {
  beforeEach(() => {
    process.env.AGENTIQ_API_BASE_URL = "https://api.example.test";
    process.env.AGENTIQ_API_ACCESS_TOKEN = "service-token";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.AGENTIQ_API_BASE_URL;
    delete process.env.AGENTIQ_API_ACCESS_TOKEN;
  });

  it("converts an HTML upstream failure to structured JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html>failure</html>", {
          status: 500,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    const response = await proxyAgentIq(
      "/ingest",
      { method: "POST" },
      "proxy-request",
    );

    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({
      code: "http_500",
      detail: "AgentIQ API request failed with HTTP 500",
      request_id: "proxy-request",
    });
  });

  it("converts an empty successful response to a structured 502", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null)));

    const response = await proxyAgentIq(
      "/collections",
      { method: "GET" },
      "empty-request",
    );

    expect(response.status).toBe(502);
    const payload = await response.json();
    expect(payload.code).toBe("invalid_upstream_response");
    expect(payload.request_id).toBe("empty-request");
  });

  it("returns structured JSON when the upstream is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const response = await proxyAgentIq(
      "/collections",
      { method: "GET" },
      "offline-request",
    );

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      code: "api_unavailable",
      request_id: "offline-request",
    });
  });
});
