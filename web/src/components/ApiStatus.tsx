import { useEffect, useState } from "react";
import { checkConnection, getApiBaseUrl } from "../api/client";

type Status = "checking" | "connected" | "disconnected";

/** Polls the local REST API once on mount and on a slow interval
 * (connection state can change if the user starts/stops `structnode
 * api serve` while this page is open). Building/analyzing a model
 * requires this connection -- the builder UI must never let the user
 * believe something was validated/solved when the backend was
 * actually unreachable. */
export function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const result = await checkConnection();
      if (!cancelled) setStatus(result.ok ? "connected" : "disconnected");
    };
    check();
    const interval = setInterval(check, 10_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (status === "connected") {
    return (
      <div className="api-status api-status--ok">
        <span className="api-status__dot" /> API connected ({getApiBaseUrl()})
      </div>
    );
  }

  return (
    <div className="api-status api-status--bad">
      <span className="api-status__dot" />
      {status === "checking" ? "Checking API connection…" : "API not reachable"}
      {status === "disconnected" && (
        <p className="api-status__help">
          Building and analyzing a model needs the local REST API. Run{" "}
          <code>uv run structnode api serve</code> and reload, or check that it's running at{" "}
          <code>{getApiBaseUrl()}</code>.
        </p>
      )}
    </div>
  );
}
