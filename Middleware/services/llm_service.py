import os

def get_severity(score: float, anomaly_count: int, total: int) -> str:
    ratio = anomaly_count / total if total > 0 else 0
    if score > 0.8 or ratio > 0.3:
        return "CRITICAL"
    elif score > 0.5 or ratio > 0.15:
        return "HIGH"
    elif score > 0.2 or ratio > 0.05:
        return "MEDIUM"
    else:
        return "LOW"

def generate_incident_report(
    channel: str,
    score: float,
    anomaly_count: int,
    total_windows: int,
    threshold: float,
    device: str
) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        severity = get_severity(score, anomaly_count, total_windows)
        ratio = round((anomaly_count / total_windows) * 100, 2) if total_windows > 0 else 0

        prompt = f"""You are a NASA spacecraft telemetry analyst AI.
Analyze the following anomaly detection result and generate a concise incident report.

Channel: {channel}
Severity: {severity}
Max Anomaly Score: {score:.4f}
Detection Threshold: {threshold}
Anomalous Windows: {anomaly_count} out of {total_windows} ({ratio}%)
Inference Device: {device}

Write a 3-4 sentence incident report that includes:
1. What was detected and on which channel
2. The severity and what it implies for the spacecraft subsystem
3. A recommended action for the operations team

Keep it professional and concise like a real NASA operations report."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    except Exception as e:
        severity = get_severity(score, anomaly_count, total_windows)
        ratio = round((anomaly_count / total_windows) * 100, 2) if total_windows > 0 else 0
        return (
            f"INCIDENT REPORT — Channel {channel} | Severity: {severity}\n"
            f"Anomaly detected with score {score:.4f} exceeding threshold {threshold}. "
            f"{anomaly_count} anomalous windows detected out of {total_windows} total ({ratio}%). "
            f"Recommend immediate review of subsystem telemetry for channel {channel}."
        )