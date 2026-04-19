"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(formData: FormData) {
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: String(formData.get("username") ?? ""),
        password: String(formData.get("password") ?? ""),
      }),
    });
    const data = await response.json();
    setLoading(false);
    if (!response.ok) {
      setMessage(data.detail ?? "Login failed.");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <form className="card stack login-card" action={submit}>
      <p className="muted">CyberRed Secure Access</p>
      <h1>Sign in</h1>
      <input className="input" name="username" placeholder="admin" required />
      <input className="input" name="password" placeholder="password" required type="password" />
      <button className="button" disabled={loading} type="submit">{loading ? "Signing in..." : "Sign in"}</button>
      {message ? <p className="muted">{message}</p> : null}
    </form>
  );
}
