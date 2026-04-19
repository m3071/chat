import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { authEnabled, sessionCookieName, verifySession } from "../../../../lib/auth";

export async function GET() {
  if (!authEnabled()) {
    return NextResponse.json({ user: "local", role: "admin", auth_enabled: false });
  }
  const cookieStore = await cookies();
  const session = verifySession(cookieStore.get(sessionCookieName())?.value);
  if (!session) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }
  return NextResponse.json({ user: session.sub, role: session.role, auth_enabled: true });
}
