import { NextResponse } from "next/server";

const apiBaseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const internalApiKey = process.env.INTERNAL_API_KEY;

export async function POST() {
  const response = await fetch(`${apiBaseUrl}/api/demo/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(internalApiKey ? { "X-Internal-Api-Key": internalApiKey } : {}),
    },
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
