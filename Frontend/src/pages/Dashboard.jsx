import { useState } from "react";
import { useAnomalyData } from "../hooks/useAnomalyData";
import AnomalyChart from "../components/AnomalyChart";
import HeatmapGrid from "../components/HeatmapGrid";
import ChannelSelector from "../components/ChannelSelector";
import { RefreshCw, LayoutDashboard, Cpu, Activity, Zap, AlertTriangle } from "lucide-react";

export default function Dashboard({ selectedModel }) {
  const [channel, setChannel] = useState("T-1");
  const { data, loading, error, refetch } = useAnomalyData(channel, 5000, selectedModel);

  return (
    <div style={{ color: "#fff", display: "flex", flexDirection: "column", gap: 24, paddingBottom: 40 }}>
      {/* Header Controls */}
      <div className="glass-panel" style={{ padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <LayoutDashboard size={20} color="var(--primary)" />
          <h2 style={{ margin: 0, fontSize: 16 }}>Live Telemetry Monitor</h2>
        </div>
        
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <ChannelSelector value={channel} onChange={setChannel} />
          <button 
            onClick={refetch} 
            disabled={loading} 
            className="btn btn-primary"
            style={{ width: 100, justifyContent: "center" }}
          >
            {loading ? <RefreshCw size={16} className="animate-pulse" style={{ animation: "spin 1s linear infinite" }} /> : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-panel" style={{ padding: 16, borderLeft: "4px solid var(--critical)", color: "var(--critical)" }}>
          <div style={{ fontSize: 12, textTransform: "uppercase", fontWeight: 600, marginBottom: 4 }}>Error</div>
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Key Metrics Row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 24 }}>
            {[
              { label: "Total Windows", value: data.total_windows, icon: Activity, color: "var(--text-main)" },
              { label: "Anomalies", value: data.anomaly_count, icon: AlertTriangle, color: data.anomaly_count > 0 ? "var(--critical)" : "var(--success)" },
              { label: "Threshold", value: data.threshold?.toFixed(2), icon: Zap, color: "var(--medium)" },
              { label: "Device", value: data.device?.toUpperCase(), icon: Cpu, color: "var(--primary)" },
            ].map((m) => (
              <div key={m.label} className="glass-panel" style={{ padding: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 500 }}>
                    {m.label}
                  </div>
                  <m.icon size={16} color={m.color} style={{ opacity: 0.8 }} />
                </div>
                <div style={{ fontSize: 28, fontWeight: 600, color: m.color, fontFamily: "var(--font-mono)" }}>
                  {m.value}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24 }}>
            {/* Chart */}
            <div className="glass-panel" style={{ padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
                <Activity size={18} color="var(--primary)" />
                <h3 style={{ margin: 0, fontSize: 15 }}>Anomaly Score Timeseries — {channel}</h3>
              </div>
              <div style={{ height: 320 }}>
                <AnomalyChart
                  scores={data.scores}
                  threshold={data.threshold}
                  channel={channel}
                />
              </div>
            </div>

            {/* Heatmap */}
            <div className="glass-panel" style={{ padding: 24 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
                <LayoutDashboard size={18} color="var(--primary)" />
                <h3 style={{ margin: 0, fontSize: 15 }}>Spatial Heatmap</h3>
              </div>
              <HeatmapGrid anomalies={data.anomalies} threshold={data.threshold} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}