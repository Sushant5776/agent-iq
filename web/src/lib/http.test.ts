import { describe, expect, it } from "vitest";

import { requireApiPayload } from "./http";

describe("API response parsing", () => {
  it("preserves a structured 400 error and request id", async () => {
    const response = new Response(
      JSON.stringify({ detail: "Malformed document", request_id: "request-400" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );

    await expect(requireApiPayload(response, "Upload failed.")).rejects.toThrow(
      "Malformed document (request request-400)",
    );
    expect(response.bodyUsed).toBe(true);
  });

  it("turns a plain-text 413 into an actionable upload error", async () => {
    const response = new Response("Payload Too Large", { status: 413 });

    await expect(requireApiPayload(response, "Upload failed.")).rejects.toThrow(
      "Upload rejected: HTTP 413. Choose a file no larger than 4 MiB.",
    );
  });

  it("does not expose an HTML 500 page as a JSON parsing error", async () => {
    const response = new Response("<html>Internal Server Error</html>", {
      status: 500,
      headers: { "Content-Type": "text/html" },
    });

    await expect(requireApiPayload(response, "Upload failed.")).rejects.toThrow(
      "Upload failed. HTTP 500.",
    );
  });

  it("handles an empty 502 response", async () => {
    const response = new Response(null, { status: 502 });

    await expect(requireApiPayload(response, "Collections failed.")).rejects.toThrow(
      "Collections failed. HTTP 502.",
    );
  });

  it("uses the stable timeout message for a structured 504", async () => {
    const response = new Response(
      JSON.stringify({ detail: "Gateway Timeout", request_id: "request-504" }),
      { status: 504 },
    );

    await expect(requireApiPayload(response, "Upload failed.")).rejects.toThrow(
      "Ingestion timed out: HTTP 504. Try a smaller document. (request request-504)",
    );
  });
});
