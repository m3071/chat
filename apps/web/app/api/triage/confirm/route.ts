const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
const internalApiKey = process.env.INTERNAL_API_KEY;

export async function POST(request: Request) {
  const body = await request.text();
  const response = await fetch(`${apiBaseUrl}/api/triage/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(internalApiKey ? { "X-Internal-Api-Key": internalApiKey } : {}),
    },
    body,
  });

  return new Response(await response.text(), {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
