export default function HeatmapGrid({ anomalies = [], threshold = 0.5 }) {
  const gridData = anomalies.slice(0, 100);

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {gridData.map((a, i) => {
        const intensity = Math.min(a.score / (threshold * 2), 1);
        const isAnomaly = a.score > threshold;
        
        let bg, shadow, border;
        
        if (isAnomaly) {
          bg = `rgba(255, 51, 102, ${Math.max(intensity, 0.4)})`;
          shadow = `0 0 10px rgba(255, 51, 102, ${intensity * 0.8})`;
          border = `1px solid rgba(255, 51, 102, 0.6)`;
        } else {
          bg = `rgba(0, 229, 255, ${Math.max(intensity * 0.5, 0.05)})`;
          shadow = "none";
          border = "1px solid var(--border-color)";
        }
        
        return (
          <div
            key={i}
            title={`Window ${a.index}: score ${a.score.toFixed(4)}`}
            style={{
              width: "calc(10% - 3.6px)", 
              aspectRatio: "1/1",
              borderRadius: 4,
              background: bg,
              boxShadow: shadow,
              border: border,
              transition: "all 0.2s ease",
              cursor: "crosshair"
            }}
          />
        );
      })}
    </div>
  );
}