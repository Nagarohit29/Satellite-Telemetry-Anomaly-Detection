import { useState, useEffect } from "react";
import { getBackendHealth } from "../api/endpoints";

export default function StatusBar() {
  const [health, setHealth] = useState(null);
  const [middlewareOk, setMiddlewareOk] = useState(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await getBackendHealth();
        setHealth(data);
        setMiddlewareOk(true);
      } catch {
        setHealth({ status: "unreachable", cuda: false, device: "unknown" });
        setMiddlewareOk(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const dot = (ok) => (
    <span style={{
      display: "inline-block",
      width: 8, height: 8,
      borderRadius: "50%",
      background: ok ? "#1D9E75" : "#E24B4A",
      marginRight: 6
    }} />
  );

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 24,
      padding: "6px 20px",
      background: "#080814",
      borderBottom: "1px solid #1a1a3a",
      fontSize: 11,
      color: "#888",
      flexWrap: "wrap"
    }}>
      <span>
        {dot(middlewareOk)}
        Middleware: {middlewareOk ? "online" : "offline"}
      </span>

      <span>
        {dot(health?.status === "healthy")}
        Backend: {health?.status ?? "connecting..."}
      </span>

      <span>
        {dot(health?.cuda)}
        CUDA: {health?.cuda ? "enabled" : "disabled"}
      </span>

      <span style={{ color: "#666" }}>
        Device: {health?.device ?? "—"}
      </span>

      <span style={{ marginLeft: "auto", color: "#444", fontSize: 10 }}>
        SatelliteAD v1.0 · NASA SMAP/MSL · TranAD Model
      </span>
    </div>
  );
}