import { NextResponse } from "next/server";

import { authenticate, sessionCookieName, signSession } from "../../../../lib/auth";

export async function POST(request: Request) {
  const payload = await request.json();
  const session = authenticate(String(payload.username ?? ""), String(payload.password ?? ""));
  if (!session) {
    return NextResponse.json({ detail: "Invalid username or password, or ADMIN_PASSWORD is not configured." }, { status: 401 });
  }
  const response = NextResponse.json({ user: session.sub, role: session.role });
  response.cookies.set(sessionCookieName(), signSession(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return response;
}
