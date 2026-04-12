import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend
} from "recharts";

export default function AnomalyChart({ scores = [], threshold = 0.5, channel = "T-1" }) {
  const chartData = scores.map((score, i) => ({
    index: i,
    score: parseFloat(score.toFixed(4)),
    threshold: threshold,
    anomaly: score > threshold ? score : null,
  }));

  return (
    <div style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer>
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
          <XAxis dataKey="index" tick={{ fontSize: 11 }} stroke="#888" />
          <YAxis tick={{ fontSize: 11 }} stroke="#888" />
          <Tooltip
            contentStyle={{ background: "#1a1a2e", border: "1px solid #444", fontSize: 12 }}
          />
          <Legend />
          <ReferenceLine y={threshold} stroke="#E24B4A" strokeDasharray="4 4" label="threshold" />
          <Line
            type="monotone" dataKey="score" stroke="#378ADD"
            dot={false} strokeWidth={1.5} name={`${channel} score`}
          />
          <Line
            type="monotone" dataKey="anomaly" stroke="#E24B4A"
            dot={{ r: 3, fill: "#E24B4A" }} strokeWidth={0} name="anomaly"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}