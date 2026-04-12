export default function HeatmapGrid({ anomalies = [], threshold = 0.5 }) {
  const gridData = anomalies.slice(0, 100);

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
      {gridData.map((a, i) => {
        const intensity = Math.min(a.score / (threshold * 2), 1);
        const r = Math.round(intensity * 220);
        const g = Math.round((1 - intensity) * 150);
        return (
          <div
            key={i}
            title={`Window ${a.index}: score ${a.score.toFixed(4)}`}
            style={{
              width: 14, height: 14, borderRadius: 2,
              background: `rgb(${r}, ${g}, 60)`,
              opacity: 0.85
            }}
          />
        );
      })}
    </div>
  );
}