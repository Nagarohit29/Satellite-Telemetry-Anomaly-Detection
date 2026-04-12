import { useState } from "react";
import { useAnomalyData } from "../hooks/useAnomalyData";
import AnomalyChart from "../components/AnomalyChart";
import HeatmapGrid from "../components/HeatmapGrid";
import ChannelSelector from "../components/ChannelSelector";

export default function Dashboard() {
  const [channel, setChannel] = useState("T-1");
  const { data, loading, error, refetch } = useAnomalyData(channel, 5000);

  return (
    <div style={{ padding: 24, color: "#fff" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Live Anomaly Monitor</h2>
        <ChannelSelector value={channel} onChange={setChannel} />
        <button onClick={refetch} disabled={loading} style={{ padding: "6px 14px", borderRadius: 6 }}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div style={{ color: "#E24B4A", marginBottom: 12, fontSize: 13 }}>
          Error: {error}
        </div>
      )}

      {data && (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
            {[
              { label: "Total Windows", value: data.total_windows },
              { label: "Anomalies", value: data.anomaly_count },
              { label: "Threshold", value: data.threshold?.toFixed(2) },
              { label: "Device", value: data.device?.toUpperCase() },
            ].map((m) => (
              <div key={m.label} style={{
                background: "#1a1a2e", borderRadius: 8,
                padding: "12px 18px", minWidth: 120
              }}>
                <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>{m.label}</div>
                <div style={{ fontSize: 20, fontWeight: 500 }}>{m.value}</div>
              </div>
            ))}
          </div>

          <div style={{ background: "#1a1a2e", borderRadius: 10, padding: 16, marginBottom: 20 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#aaa" }}>
              Anomaly Score — {channel}
            </h3>
            <AnomalyChart
              scores={data.scores}
              threshold={data.threshold}
              channel={channel}
            />
          </div>

          <div style={{ background: "#1a1a2e", borderRadius: 10, padding: 16 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 14, color: "#aaa" }}>
              Anomaly Heatmap (first 100 windows)
            </h3>
            <HeatmapGrid anomalies={data.anomalies} threshold={data.threshold} />
          </div>
        </>
      )}
    </div>
  );
}