import { NextResponse } from "next/server";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
const internalApiKey = process.env.INTERNAL_API_KEY;

export async function GET() {
  const response = await fetch(`${apiBaseUrl}/api/diagnostics`, {
    headers: {
      "Content-Type": "application/json",
      ...(internalApiKey ? { "X-Internal-Api-Key": internalApiKey } : {}),
    },
    cache: "no-store",
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
