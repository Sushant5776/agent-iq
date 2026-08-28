import { proxyAgentIq } from "@/lib/api-proxy";

export async function GET() {
  return proxyAgentIq("/collections", { method: "GET" });
}
