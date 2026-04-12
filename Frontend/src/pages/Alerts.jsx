import { useAlerts } from "../hooks/useAlerts";
import AlertCard from "../components/AlertCard";

export default function Alerts() {
  const { alerts, loading, deleteAlerts } = useAlerts(8000);

  return (
    <div style={{ padding: 24, color: "#fff" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Incident Alerts</h2>
        <span style={{ fontSize: 13, color: "#888" }}>{alerts.length} alerts</span>
        <button
          onClick={deleteAlerts}
          style={{ marginLeft: "auto", padding: "6px 14px", borderRadius: 6, color: "#E24B4A" }}
        >
          Clear All
        </button>
      </div>

      {loading && <div style={{ color: "#888", fontSize: 13 }}>Loading alerts...</div>}

      {alerts.length === 0 && !loading && (
        <div style={{ color: "#555", fontSize: 13 }}>
          No alerts yet. Anomalies will appear here automatically.
        </div>
      )}

      {alerts.map((alert) => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </div>
  );
}