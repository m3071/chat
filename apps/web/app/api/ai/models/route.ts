import { NextResponse } from "next/server";

const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
const internalApiKey = process.env.INTERNAL_API_KEY;

function headers() {
  return {
    "Content-Type": "application/json",
    ...(internalApiKey ? { "X-Internal-Api-Key": internalApiKey } : {}),
  };
}

export async function GET() {
  const response = await fetch(`${apiBaseUrl}/api/ai/models`, { headers: headers(), cache: "no-store" });
  return NextResponse.json(await response.json(), { status: response.status });
}

export async function POST(request: Request) {
  const response = await fetch(`${apiBaseUrl}/api/ai/models`, {
    method: "POST",
    headers: headers(),
    body: await request.text(),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
