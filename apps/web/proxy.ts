import { NextRequest, NextResponse } from "next/server";

const publicPrefixes = ["/login", "/api/auth", "/_next", "/favicon.ico"];
const cookieName = "cyberred_session";

export async function proxy(request: NextRequest) {
  if (process.env.AUTH_ENABLED !== "true") {
    return NextResponse.next();
  }
  const { pathname } = request.nextUrl;
  if (publicPrefixes.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }
  const session = request.cookies.get(cookieName)?.value;
  if (session && (await verifySession(session))) {
    return NextResponse.next();
  }
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("next", pathname);
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!.*\\..*).*)"],
};

async function verifySession(value: string) {
  const [encoded, providedSignature] = value.split(".", 2);
  if (!encoded || !providedSignature) {
    return false;
  }
  const expected = await hmac(encoded);
  if (providedSignature !== expected) {
    return false;
  }
  try {
    const normalized = encoded.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded));
    return typeof payload.exp === "number" && payload.exp > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

async function hmac(value: string) {
  const secret = process.env.APP_SESSION_SECRET ?? process.env.INTERNAL_API_KEY ?? "dev-session-secret";
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return base64Url(new Uint8Array(signature));
}

function base64Url(bytes: Uint8Array) {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}
