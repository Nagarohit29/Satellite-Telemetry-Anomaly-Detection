const severityColors = {
  CRITICAL: { bg: "rgba(255, 51, 102, 0.1)", border: "var(--critical)", text: "var(--critical)", shadow: "0 0 15px rgba(255, 51, 102, 0.2)" },
  HIGH:     { bg: "rgba(255, 136, 0, 0.1)", border: "var(--high)", text: "var(--high)", shadow: "0 0 10px rgba(255, 136, 0, 0.15)" },
  MEDIUM:   { bg: "rgba(255, 204, 0, 0.1)", border: "var(--medium)", text: "var(--medium)", shadow: "none" },
  LOW:      { bg: "rgba(0, 229, 255, 0.05)", border: "var(--low)", text: "var(--low)", shadow: "none" },
};

export default function AlertCard({ alert }) {
  const colors = severityColors[alert.severity] || severityColors.LOW;
  const time = new Date(alert.timestamp).toLocaleTimeString();

  return (
    <div className="glass-panel" style={{
      background: colors.bg, 
      borderLeft: `4px solid ${colors.border}`,
      boxShadow: colors.shadow,
      padding: "16px 20px", 
      marginBottom: 16
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <div className={`badge badge-${alert.severity.toLowerCase()}`}>
          {alert.severity}
        </div>
        <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{time}</span>
      </div>
      <div style={{ fontSize: 14, color: "var(--text-main)", marginBottom: 8, display: "flex", gap: 16 }}>
        <span>Channel: <strong style={{ color: "var(--primary)" }}>{alert.channel}</strong></span>
        <span>Score: <strong style={{ color: colors.text }}>{alert.score.toFixed(4)}</strong></span>
      </div>
      <p style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
        {alert.report}
      </p>
    </div>
  );
}