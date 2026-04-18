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
    <div style={{ width: "100%", height: "100%" }}>
      <ResponsiveContainer>
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
          <XAxis dataKey="index" tick={{ fontSize: 11, fill: "var(--text-muted)" }} stroke="transparent" />
          <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} stroke="transparent" />
          <Tooltip
            contentStyle={{ 
              background: "rgba(5, 5, 10, 0.9)", 
              border: "1px solid var(--border-glow)", 
              fontSize: 12,
              borderRadius: 8,
              backdropFilter: "blur(10px)"
            }}
            itemStyle={{ color: "var(--text-main)" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
          <ReferenceLine y={threshold} stroke="var(--critical)" strokeDasharray="4 4" label={{ value: "critical threshold", fill: "var(--critical)", fontSize: 10, position: "insideTopLeft" }} />
          <Line
            type="monotone" dataKey="score" stroke="var(--primary)"
            dot={false} strokeWidth={2} name={`${channel} score`}
            activeDot={{ r: 4, fill: "var(--bg-dark)", stroke: "var(--primary)", strokeWidth: 2 }}
          />
          <Line
            type="monotone" dataKey="anomaly" stroke="var(--critical)"
            dot={{ r: 4, fill: "var(--critical)", stroke: "rgba(255, 51, 102, 0.3)", strokeWidth: 4 }} 
            strokeWidth={0} name="anomaly"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}