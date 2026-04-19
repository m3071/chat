const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
const internalApiKey = process.env.INTERNAL_API_KEY;

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const url = new URL(request.url);
  const format = url.searchParams.get("format") ?? "md";
  const response = await fetch(`${apiBaseUrl}/api/incidents/${id}/report?format=${encodeURIComponent(format)}`, {
    headers: {
      ...(internalApiKey ? { "X-Internal-Api-Key": internalApiKey } : {}),
    },
    cache: "no-store",
  });
  return new Response(await response.text(), {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "text/plain",
      "Content-Disposition": response.headers.get("Content-Disposition") ?? `attachment; filename="incident-${id}.${format}"`,
    },
  });
}
