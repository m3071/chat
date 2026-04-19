"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DemoIncidentButton() {
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function generate() {
    setLoading(true);
    setMessage("");
    const response = await fetch("/api/demo/generate", { method: "POST" });
    const data = await response.json();
    setLoading(false);
    setMessage(data.message ?? "Demo incident generated.");
    router.refresh();
  }

  return (
    <div className="demo-action">
      <button className="button secondary" type="button" onClick={generate} disabled={loading}>
        {loading ? "Generating..." : "Generate Demo Incident"}
      </button>
      {message ? <span className="muted">{message}</span> : null}
    </div>
  );
}
