import Link from "next/link";
import { LogoutButton } from "./LogoutButton";

export function Nav() {
  return (
    <nav className="nav">
      <Link href="/">Overview</Link>
      <Link href="/alerts">Alerts</Link>
      <Link href="/incidents">Incidents</Link>
      <Link href="/chat">Chat</Link>
      <Link href="/settings/ai">AI Settings</Link>
      <Link href="/diagnostics">Diagnostics</Link>
      {process.env.AUTH_ENABLED === "true" ? <LogoutButton /> : null}
    </nav>
  );
}
