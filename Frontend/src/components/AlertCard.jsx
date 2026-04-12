const severityColors = {
  CRITICAL: { bg: "#3d0000", border: "#E24B4A", text: "#ff6b6b" },
  HIGH:     { bg: "#3d1a00", border: "#EF9F27", text: "#ffb347" },
  MEDIUM:   { bg: "#1a2a00", border: "#639922", text: "#90cc44" },
  LOW:      { bg: "#001a2a", border: "#378ADD", text: "#60aaff" },
};

export default function AlertCard({ alert }) {
  const colors = severityColors[alert.severity] || severityColors.LOW;
  const time = new Date(alert.timestamp).toLocaleTimeString();

  return (
    <div style={{
      background: colors.bg, border: `1px solid ${colors.border}`,
      borderRadius: 10, padding: "14px 16px", marginBottom: 10
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: colors.text }}>
          ● {alert.severity}
        </span>
        <span style={{ fontSize: 11, color: "#888" }}>{time}</span>
      </div>
      <div style={{ fontSize: 13, color: "#ccc", marginBottom: 6 }}>
        Channel: <strong style={{ color: "#fff" }}>{alert.channel}</strong>
        &nbsp;|&nbsp; Score: <strong style={{ color: colors.text }}>
          {alert.score.toFixed(4)}
        </strong>
      </div>
      <p style={{ fontSize: 12, color: "#aaa", lineHeight: 1.6, margin: 0 }}>
        {alert.report}
      </p>
    </div>
  );
}