import { useState } from "react";
import { predict } from "../api/endpoints";
import AnomalyChart from "../components/AnomalyChart";

export default function Upload() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [channel, setChannel] = useState("T-1");

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    const text = await file.text();
    const data = text.split("\n")
      .map((v) => parseFloat(v.trim()))
      .filter((v) => !isNaN(v));
    try {
      const res = await predict(channel, data);
      setResult(res);
    } catch (err) {
      alert("Prediction failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, color: "#fff" }}>
      <h2 style={{ marginBottom: 20, fontSize: 18 }}>Upload Telemetry CSV</h2>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 20 }}>
        <input
          type="text"
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
          placeholder="Channel (e.g. T-1)"
          style={{ padding: "6px 12px", borderRadius: 6, fontSize: 13, width: 140 }}
        />
        <input type="file" accept=".csv,.txt" onChange={handleFile} />
        {loading && <span style={{ fontSize: 13, color: "#888" }}>Running inference...</span>}
      </div>

      <p style={{ fontSize: 12, color: "#666", marginBottom: 20 }}>
        Upload a plain text or CSV file with one float value per line.
      </p>

      {result && (
        <div style={{ background: "#1a1a2e", borderRadius: 10, padding: 16 }}>
          <h3 style={{ fontSize: 14, color: "#aaa", marginBottom: 12 }}>
            Results — {result.channel}
          </h3>
          <AnomalyChart
            scores={result.scores}
            threshold={result.threshold}
            channel={result.channel}
          />
          <p style={{ fontSize: 13, color: "#aaa", marginTop: 12 }}>
            Anomalies detected: <strong style={{ color: "#E24B4A" }}>
              {result.anomaly_count}
            </strong> / {result.total_windows} windows
          </p>
        </div>
      )}
    </div>
  );
}