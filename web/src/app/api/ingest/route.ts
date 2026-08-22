import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const baseUrl = process.env.AGENTIQ_API_BASE_URL;
  const token = process.env.AGENTIQ_API_ACCESS_TOKEN;
  if (!baseUrl || !token) {
    return NextResponse.json({ detail: "AgentIQ API is not configured" }, { status: 503 });
  }

  try {
    const response = await fetch(`${baseUrl}/ingest`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": request.headers.get("content-type") || "application/octet-stream",
      },
      body: await request.arrayBuffer(),
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "AgentIQ API is unavailable" }, { status: 502 });
  }
}
