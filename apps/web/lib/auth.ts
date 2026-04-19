import { createHmac, timingSafeEqual } from "crypto";

export type SessionPayload = {
  sub: string;
  role: "admin" | "analyst";
  exp: number;
};

const cookieName = "cyberred_session";

export function authEnabled() {
  return process.env.AUTH_ENABLED === "true";
}

export function sessionCookieName() {
  return cookieName;
}

export function signSession(payload: SessionPayload) {
  const encoded = Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
  return `${encoded}.${signature(encoded)}`;
}

export function verifySession(value: string | undefined): SessionPayload | null {
  if (!value || !value.includes(".")) {
    return null;
  }
  const [encoded, providedSignature] = value.split(".", 2);
  const expectedSignature = signature(encoded);
  const provided = Buffer.from(providedSignature);
  const expected = Buffer.from(expectedSignature);
  if (provided.length !== expected.length || !timingSafeEqual(provided, expected)) {
    return null;
  }
  const payload = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8")) as SessionPayload;
  if (!payload.exp || payload.exp < Math.floor(Date.now() / 1000)) {
    return null;
  }
  return payload;
}

export function authenticate(username: string, password: string): SessionPayload | null {
  const expectedUsername = process.env.ADMIN_USERNAME ?? "admin";
  const expectedPassword = process.env.ADMIN_PASSWORD ?? "";
  if (!expectedPassword) {
    return null;
  }
  if (username !== expectedUsername || password !== expectedPassword) {
    return null;
  }
  return {
    sub: username,
    role: "admin",
    exp: Math.floor(Date.now() / 1000) + 60 * 60 * 8,
  };
}

function signature(encodedPayload: string) {
  const secret = process.env.APP_SESSION_SECRET ?? process.env.INTERNAL_API_KEY ?? "dev-session-secret";
  return createHmac("sha256", secret).update(encodedPayload).digest("base64url");
}
