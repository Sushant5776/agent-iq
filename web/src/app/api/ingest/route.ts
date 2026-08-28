import {
  MAX_MULTIPART_BODY_BYTES,
  proxyAgentIq,
  proxyError,
} from "@/lib/api-proxy";

export const maxDuration = 300;

export async function POST(request: Request) {
  const requestId = crypto.randomUUID();
  const contentLength = Number(request.headers.get("content-length") || "0");
  if (contentLength > MAX_MULTIPART_BODY_BYTES) {
    return proxyError(
      413,
      "upload_too_large",
      "Upload exceeds the 4 MiB file limit",
      requestId,
    );
  }

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_MULTIPART_BODY_BYTES) {
    return proxyError(
      413,
      "upload_too_large",
      "Upload exceeds the 4 MiB file limit",
      requestId,
    );
  }

  return proxyAgentIq(
    "/ingest",
    {
      method: "POST",
      headers: {
        "Content-Type":
          request.headers.get("content-type") || "application/octet-stream",
      },
      body,
    },
    requestId,
  );
}
