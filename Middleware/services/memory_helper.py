import os
import json
import datetime
import threading

_memory_lock = threading.Lock()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERMES_DIR = os.path.join(PROJECT_ROOT, ".hermes", "memories")
MEMORY_FILE_PATH = os.path.join(HERMES_DIR, "MEMORY.md")
USER_FILE_PATH = os.path.join(HERMES_DIR, "USER.md")

DEFAULT_MEMORY_TEMPLATE = """# Spacecraft Telemetry Workspace Memory

## Last Updated
- Timestamp: N/A

## Environment & Configurations
- Active Ground Station Coordinates: Latitude: 0.0, Longitude: 0.0, Altitude: 0.0m
- Telemetry API Status (N2YO): Unconfigured / Offline

## Key Monitored Targets
- NORAD ID: None

## Subsystem Anomalies Log
*(No active anomalies logged)*

## Custom Engineer Notes & Findings
*(No custom notes recorded)*
"""

DEFAULT_USER_TEMPLATE = """# User Profile & Analyst Preferences

- User Persona: Space Operations Engineer
- Preferences: Professional, clear, domain-expert responses
"""

def get_timestamps() -> str:
    """Return local ground station time (IST, UTC+5:30) and UTC formatted time."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    # Indian Standard Time (IST) is UTC + 5:30
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    utc_str = utc_now.strftime("%Y-%m-%d %H:%M:%S UTC")
    ist_str = ist_now.strftime("%Y-%m-%d %H:%M:%S IST")
    return f"{ist_str} ({utc_str})"

def initialize_memory_files():
    """Create .hermes directory and default memories files if they are missing or corrupt."""
    os.makedirs(HERMES_DIR, exist_ok=True)
    
    # Initialize MEMORY.md if missing or corrupt (e.g. contains rate limit error messages)
    need_init = True
    if os.path.exists(MEMORY_FILE_PATH):
        try:
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if "# Spacecraft Telemetry" in content and "## Environment" in content:
                    need_init = False
        except Exception:
            pass
            
    if need_init:
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_MEMORY_TEMPLATE.strip() + "\n")
            
    # Initialize USER.md if missing
    if not os.path.exists(USER_FILE_PATH):
        with open(USER_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_USER_TEMPLATE.strip() + "\n")

def read_memory_sections() -> dict:
    """Read MEMORY.md and split it into sections based on ## headers."""
    with _memory_lock:
        initialize_memory_files()
        
        with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        # Extra check for corruption
        if "# Spacecraft Telemetry" not in content or "## Environment" not in content:
            with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(DEFAULT_MEMORY_TEMPLATE.strip() + "\n")
            content = DEFAULT_MEMORY_TEMPLATE.strip()
            
        sections = {}
        current_section = "Header"
        current_lines = []
        
        for line in content.split("\n"):
            if line.startswith("## "):
                sections[current_section] = "\n".join(current_lines).strip()
                current_section = line.replace("## ", "").strip()
                current_lines = []
            else:
                current_lines.append(line)
                
        sections[current_section] = "\n".join(current_lines).strip()
        return sections

def write_memory_sections(sections: dict):
    """Reassemble and write memory sections to MEMORY.md."""
    with _memory_lock:
        os.makedirs(HERMES_DIR, exist_ok=True)
        lines = []
        if "Header" in sections:
            lines.append(sections["Header"])
            lines.append("")
            
        ordered_sections = [
            "Last Updated",
            "Environment & Configurations",
            "Key Monitored Targets",
            "Subsystem Anomalies Log",
            "Custom Engineer Notes & Findings"
        ]
        
        for sec in ordered_sections:
            if sec in sections:
                lines.append(f"## {sec}")
                lines.append(sections[sec])
                lines.append("")
                
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")

def log_config_to_memory(lat: float, lng: float, alt: float, n2yo_configured: bool):
    """Programmatically log the ground station coordinates and API status to MEMORY.md."""
    try:
        sections = read_memory_sections()
        time_str = get_timestamps()
        
        sections["Last Updated"] = f"- Timestamp: {time_str}"
        
        status_str = "Configured / Active" if n2yo_configured else "Unconfigured / Offline"
        sections["Environment & Configurations"] = (
            f"- Active Ground Station Coordinates: Latitude: {lat}, Longitude: {lng}, Altitude: {alt}m\n"
            f"- Telemetry API Status (N2YO): {status_str}"
        )
        
        write_memory_sections(sections)
        print(f"SUCCESS: Programmatically logged ground station config to memory.")
    except Exception as e:
        print(f"WARNING: Failed to log config to memory: {e}")

def log_anomaly_to_memory(channel: str, score: float, severity: str, anomaly_count: int, total_windows: int, report_text: str):
    """Programmatically log a concise telemetry anomaly report to MEMORY.md."""
    try:
        sections = read_memory_sections()
        time_str = get_timestamps()
        
        sections["Last Updated"] = f"- Timestamp: {time_str}"
        
        # Extract title or first descriptive line of the report for summary
        summary_msg = "Telemetry threshold violation detected."
        if report_text:
            lines = [l.strip() for l in report_text.split("\n") if l.strip()]
            # First, check for an explicit Report Title
            for line in lines:
                if line.startswith("- Report Title:") or line.startswith("Report Title:"):
                    summary_msg = line.split(":", 1)[1].strip()
                    break
            else:
                # If no Report Title, check for other headers (ignoring generic Cover Section) or descriptive lines
                for line in lines:
                    if line.startswith("# ") and "cover section" not in line.lower():
                        summary_msg = line.replace("# ", "").strip()
                        break
                    elif "anomaly" in line.lower() or "flagged" in line.lower() or "deviation" in line.lower():
                        summary_msg = line
                        break
                else:
                    if lines:
                        summary_msg = lines[0]
                    
        # Strip markdown accents
        summary_msg = summary_msg.replace("**", "").replace("*", "").strip()
        if len(summary_msg) > 120:
            summary_msg = summary_msg[:117] + "..."
            
        current_log = sections.get("Subsystem Anomalies Log", "").strip()
        if "*(No active anomalies logged)*" in current_log or not current_log:
            current_log = ""
            
        new_entry = f"- [{time_str}] Channel: {channel} | Severity: {severity} | Peak Score: {score:.4f} | Windows: {anomaly_count}/{total_windows} | Summary: {summary_msg}"
        
        if current_log:
            sections["Subsystem Anomalies Log"] = f"{current_log}\n{new_entry}"
        else:
            sections["Subsystem Anomalies Log"] = new_entry
            
        write_memory_sections(sections)
        print(f"SUCCESS: Programmatically logged anomaly for channel {channel} to memory.")
    except Exception as e:
        print(f"WARNING: Failed to log anomaly to memory: {e}")
