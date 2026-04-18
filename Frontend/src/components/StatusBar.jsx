import { useState, useEffect } from "react";
import { getBackendHealth } from "../api/endpoints";
import { Server, Cpu, Satellite } from "lucide-react";

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
      width: 6, height: 6,
      borderRadius: "50%",
      background: ok ? "var(--success)" : "var(--critical)",
      boxShadow: ok ? "0 0 5px var(--success)" : "0 0 5px var(--critical)",
      marginRight: 6
    }} className={ok ? "animate-pulse" : ""} />
  );

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: 12,
      fontSize: 12,
      color: "var(--text-muted)",
    }}>
      <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: "var(--text-muted)" }}>
        System Status
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Server size={14} color="var(--primary)" />
          Middleware
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          {dot(middlewareOk)}
          <span style={{ color: middlewareOk ? "var(--success)" : "var(--critical)" }}>
            {middlewareOk ? "Online" : "Offline"}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Satellite size={14} color="var(--primary)" />
          Backend
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          {dot(health?.status === "healthy")}
          <span style={{ color: health?.status === "healthy" ? "var(--success)" : "var(--critical)" }}>
            {health?.status === "healthy" ? "Online" : "Unreachable"}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Cpu size={14} color="var(--primary)" />
          Compute
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4, maxWidth: 140 }}>
          <span 
            style={{ 
              color: "var(--text-main)", 
              fontSize: 10, 
              fontFamily: "var(--font-mono)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis"
            }}
            title={health?.device?.toUpperCase() ?? "CPU"}
          >
            {health?.device?.toUpperCase() ?? "CPU"}
          </span>
          {health?.cuda && <span style={{ color: "var(--success)", fontSize: 10, fontFamily: "var(--font-mono)", flexShrink: 0 }}>(CUDA)</span>}
        </div>
      </div>
    </div>
  );
}