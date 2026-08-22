import { NextResponse } from "next/server";

export async function GET() {
  const baseUrl = process.env.AGENTIQ_API_BASE_URL;
  const token = process.env.AGENTIQ_API_ACCESS_TOKEN;
  if (!baseUrl || !token) {
    return NextResponse.json({ detail: "AgentIQ API is not configured" }, { status: 503 });
  }

  try {
    const response = await fetch(`${baseUrl}/collections`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "AgentIQ API is unavailable" }, { status: 502 });
  }
}