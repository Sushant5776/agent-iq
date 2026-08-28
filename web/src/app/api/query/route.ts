import { proxyAgentIq } from "@/lib/api-proxy";

export async function POST(request: Request) {
  return proxyAgentIq("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
  });
}
