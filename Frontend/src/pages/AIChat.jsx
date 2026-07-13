import { useState, useEffect, useRef } from "react";
import { 
  Send, MessageSquare, Sparkles, Database, FileText, Download, 
  Cpu, Layout, RefreshCw, AlertTriangle, CheckCircle, ChevronRight, Activity, Settings, X, Upload, Trash2, Copy
} from "lucide-react";
import { 
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, 
  CartesianGrid, Tooltip, Legend, ReferenceLine, Cell 
} from "recharts";
import { sendChatMessage, getLLMModels, runCelestrakInfer, exportCSV, importReport, getAlerts, getChannels, getKeysStatus } from "../api/endpoints";
import AISettingsPanel from "../components/AISettingsPanel";

// Simple obfuscation for localStorage data to prevent casual reading
const _STORAGE_KEY = 'stad_chat_messages';
const _obfuscate = (str) => {
  try { return btoa(encodeURIComponent(str)); } catch { return str; }
};
const _deobfuscate = (str) => {
  try { return decodeURIComponent(atob(str)); } catch { return str; }
};
const safeStorageGet = (key) => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    // Try deobfuscated first (new format), fall back to raw (legacy)
    try {
      return _deobfuscate(raw);
    } catch {
      return raw; // Legacy unencoded data
    }
  } catch { return null; }
};
const safeStorageSet = (key, value) => {
  try { localStorage.setItem(key, _obfuscate(value)); } catch { /* quota exceeded */ }
};

/**
 * Sanitize HTML output to prevent XSS attacks.
 * Strips dangerous tags/attributes while preserving safe formatting.
 */
const ALLOWED_TAGS = new Set([
  'p','br','strong','em','code','pre','table','thead','tbody','tr','th','td',
  'ul','ol','li','h1','h2','h3','h4','h5','h6','blockquote','a','span','div','hr'
]);
const ALLOWED_ATTRS = new Set(['style','href','class']);

const sanitizeHTML = (html) => {
  if (!html) return "";
  const doc = new DOMParser().parseFromString(html, 'text/html');
  if (!doc || !doc.body) return "";
  const walk = (node) => {
    if (node.nodeType === 3) return; // text node
    if (node.nodeType === 1) { // element
      if (!ALLOWED_TAGS.has(node.tagName.toLowerCase())) {
        node.replaceWith(...node.childNodes);
        return;
      }
      // Remove disallowed attributes
      for (const attr of [...node.attributes]) {
        if (!ALLOWED_ATTRS.has(attr.name.toLowerCase())) {
          node.removeAttribute(attr.name);
        }
        // Block javascript: URLs
        if (attr.name === 'href' && attr.value.toLowerCase().trim().startsWith('javascript:')) {
          node.removeAttribute(attr.name);
        }
      }
    }
    for (const child of [...node.childNodes]) {
      walk(child);
    }
  };
  // Walk children of body — never touch the body container itself
  for (const child of [...doc.body.childNodes]) {
    walk(child);
  }
  return doc.body.innerHTML;
};

const parseMarkdownToHTML = (md) => {
  if (!md) return "";
  
  // Escape HTML to prevent XSS
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 1. Code blocks: ```code```
  html = html.replace(/```([\s\S]+?)```/g, (match, code) => {
    return `<pre style="background: rgba(0,0,0,0.45); border: 1px solid rgba(0,229,255,0.15); border-left: 3px solid var(--primary); padding: 12px; border-radius: 6px; font-family: monospace; font-size: 12.5px; overflow-x: auto; margin: 12px 0; color: #64ffda;"><code style="white-space: pre-wrap;">${code.trim()}</code></pre>`;
  });

  // 2. Headings
  html = html.replace(/^# (.*?)$/gm, '<h1 style="font-family: var(--font-orbitron); font-size: 18px; font-weight: 700; color: var(--primary); margin: 24px 0 12px; border-bottom: 1px solid rgba(0,229,255,0.25); padding-bottom: 8px; letter-spacing: 1px;">$1</h1>');
  html = html.replace(/^## (.*?)$/gm, '<h2 style="font-family: var(--font-orbitron); font-size: 14px; font-weight: 700; color: #fff; margin: 20px 0 10px; border-left: 3px solid var(--primary); padding-left: 8px; letter-spacing: 0.5px;">$1</h2>');
  html = html.replace(/^### (.*?)$/gm, '<h3 style="font-family: var(--font-orbitron); font-size: 12.5px; font-weight: 600; color: #e0e0e0; margin: 16px 0 8px; text-transform: uppercase;">$1</h3>');

  // 3. Bold: **text**
  html = html.replace(/\*\*([^*]+?)\*\*/g, '<strong style="color: var(--primary); font-weight: 600;">$1</strong>');

  // 4. Bullet lists: - item or * item
  html = html.replace(/^(?:-|\*)\s+(.*?)$/gm, '<li style="margin-bottom: 6px; font-size: 13px; line-height: 1.5; color: #e0e0e0;">$1</li>');
  html = html.replace(/((?:<li style=".*?">.*?<\/li>\s*)+)/g, '<ul style="margin: 8px 0 16px; padding-left: 20px; list-style-type: square;">$1</ul>');

  // 5. Tables
  const lines = html.split("\n");
  let inTable = false;
  let tableHTML = "";
  let processedLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith("|") && line.endsWith("|")) {
      const cells = line.split("|").map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
      
      if (!inTable) {
        inTable = true;
        tableHTML = '<div style="overflow-x: auto; margin: 18px 0; border: 1px solid rgba(0, 229, 255, 0.15); border-radius: 6px;"><table style="width: 100%; border-collapse: collapse; font-size: 12.5px; background: rgba(3, 3, 7, 0.5);">';
        tableHTML += '<thead><tr style="background: rgba(0, 229, 255, 0.08); border-bottom: 1px solid rgba(0, 229, 255, 0.2);">';
        cells.forEach(c => {
          tableHTML += `<th style="padding: 10px 12px; text-align: left; font-weight: 600; color: var(--primary);">${c}</th>`;
        });
        tableHTML += '</tr></thead><tbody>';
      } else {
        if (line.includes("---") || line.includes("===")) {
          continue;
        }
        tableHTML += '<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">';
        cells.forEach(c => {
          tableHTML += `<td style="padding: 10px 12px; color: #ddd;">${c}</td>`;
        });
        tableHTML += '</tr>';
      }
    } else {
      if (inTable) {
        tableHTML += '</tbody></table></div>';
        processedLines.push(tableHTML);
        inTable = false;
        tableHTML = "";
      }
      processedLines.push(line);
    }
  }
  if (inTable) {
    tableHTML += '</tbody></table></div>';
    processedLines.push(tableHTML);
  }
  html = processedLines.join("\n");

  // 6. Horizontal Rules
  html = html.replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid rgba(0, 229, 255, 0.15); margin: 20px 0;" />');

  // 7. Paragraphs & Linebreaks
  html = html.replace(/\n\n/g, '<div style="height: 12px;"></div>');
  html = html.replace(/\n/g, "<br />");

  return html;
};

export default function AIChat({ 
  selectedModel: initialModel, 
  activeTelemetry,
  observerLat,
  observerLng,
  observerAlt
}) {
  const [messages, setMessages] = useState(() => {
    try {
      const saved = safeStorageGet("stad_chat_messages");
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error("Failed to load chat history:", e);
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const abortControllerRef = useRef(null);

  // Clean up abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Save messages to local storage whenever they change
  useEffect(() => {
    try {
      safeStorageSet("stad_chat_messages", JSON.stringify(messages));
    } catch (e) {
      console.error("Failed to save chat history:", e);
    }
  }, [messages]);

  const handleClearHistory = () => {
    setMessages([]);
    try {
      localStorage.removeItem("stad_chat_messages");
    } catch (e) {
      console.error("Failed to clear chat history:", e);
    }
  };

  const handleCopyText = (text, idx) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        setCopiedIdx(idx);
        setTimeout(() => setCopiedIdx(null), 2000);
      })
      .catch((err) => console.error("Could not copy text: ", err));
  };

  const handleCancelQuery = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };


  
  // Custom API configuration states
  const [trackingMode, setTrackingMode] = useState("constellation"); // "constellation" or "satellite"
  const [targetName, setTargetName] = useState("noaa"); // default group or catalog id
  
  // Models configuration
  const [models, setModels] = useState([]);
  const [activeModel, setActiveModel] = useState(initialModel || "");
  const [showSettings, setShowSettings] = useState(false);
  const settingsPanelRef = useRef(null);
  
  // Chart refs to enable downloading
  const chartRefs = useRef({});
  const messagesEndRef = useRef(null);

  // Close preferences panel on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        showSettings &&
        settingsPanelRef.current &&
        !settingsPanelRef.current.contains(event.target) &&
        !event.target.closest("#ai-preferences-toggle-btn")
      ) {
        setShowSettings(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showSettings]);

  // Import Report states
  const [showImportModal, setShowImportModal] = useState(false);
  const [importReportType, setImportReportType] = useState("Business Report");
  const [importInstructions, setImportInstructions] = useState("");
  const [importFile, setImportFile] = useState(null);

  // System-wide context states to pass to the AI model
  const [allChannels, setAllChannels] = useState([]);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [keysStatus, setKeysStatus] = useState(null);

  // Fetch channels, alerts, and keys configuration status periodically for system context
  useEffect(() => {
    async function loadSystemMetadata() {
      try {
        const [channelsRes, alertsRes, keysRes] = await Promise.all([
          getChannels().catch(() => ({ channels: [] })),
          getAlerts().catch(() => []),
          getKeysStatus().catch(() => ({}))
        ]);
        setAllChannels(channelsRes.channels || []);
        setRecentAlerts(alertsRes || []);
        setKeysStatus(keysRes || {});
      } catch (err) {
        console.error("Failed to load system metadata in AI Chat:", err);
      }
    }
    loadSystemMetadata();
    const interval = setInterval(loadSystemMetadata, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleImportFileChange = (e) => {
    const file = e.target.files[0];
    if (file) setImportFile(file);
  };

  const handleRunImport = async () => {
    if (!importFile || loading) return;
    
    setShowImportModal(false);
    setLoading(true);
    
    const fileName = importFile.name;
    let userPrompt = `[Uploaded File: ${fileName} for normalization as ${importReportType}]`;
    if (importInstructions.trim()) {
      userPrompt += `\n*Instructions: ${importInstructions}*`;
    }
    const newMessages = [...messages, { role: "user", content: userPrompt }];
    setMessages(newMessages);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const text = await importFile.text();
      const res = await importReport(text, importReportType, activeModel, importInstructions, controller.signal);
      
      setMessages([...newMessages, { role: "assistant", content: res.response }]);
    } catch (err) {
      if (
        err.name === "CanceledError" || 
        err.message === "canceled" || 
        err.code === "ERR_CANCELED" ||
        err.message?.includes("canceled") ||
        err.message?.includes("aborted")
      ) {
        setMessages([...newMessages, {
          role: "assistant",
          content: "*Inference cancelled by user.*"
        }]);
      } else {
        setMessages([...newMessages, { 
          role: "assistant", 
          content: `❌ **Failed to import report**: ${err.message}`,
          isError: true 
        }]);
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setLoading(false);
      setImportFile(null);
      setImportInstructions("");
    }
  };

  // Fetch available models on load
  useEffect(() => {
    async function loadModels() {
      try {
        const res = await getLLMModels();
        if (res.models && res.models.length > 0) {
          setModels(res.models);
          // Set first available model if none active
          if (!activeModel) {
            const available = res.models.find(m => m.available);
            if (available) setActiveModel(available.id);
          }
        }
      } catch (err) {
        console.error("Failed to load models:", err);
      }
    }
    loadModels();
  }, [activeModel]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const serializeDashboardContext = (activeTelemetry) => {
    let contextStr = `### System Subsystems & Channels\n`;
    if (allChannels && allChannels.length > 0) {
      contextStr += `- **Monitored Subsystem Channels**: ${allChannels.join(", ")}\n`;
    } else {
      contextStr += `- **Monitored Subsystem Channels**: T-1 (default)\n`;
    }

    if (keysStatus) {
      contextStr += `- **Telemetry API Status**: N2YO Key is ${keysStatus.n2yo ? "CONFIGURED" : "NOT CONFIGURED"}\n`;
    }
    
    if (activeTelemetry) {
      const { activeData, activeChannel, thresholdVal, observerLat, observerLng, observerAlt, selectedRecording } = activeTelemetry;
      contextStr += `\n### Active Subsystem Telemetry Details\n`;
      contextStr += `- **Currently Monitored Subsystem**: Channel ${activeChannel || "none"}\n`;
      contextStr += `- **Data Source**: ${activeData ? (activeData.telemetrySource || activeData.source || "Unknown") : "Unknown"}\n`;
      contextStr += `- **Observer Ground Station coordinates**: Latitude = ${observerLat || 0.0}°, Longitude = ${observerLng || 0.0}°, Altitude = ${observerAlt || 0.0}m\n`;
      contextStr += `- **Anomaly Score Threshold**: ${thresholdVal || 0.15}\n`;
      
      if (selectedRecording) {
        contextStr += `\n### Loaded Recorded Replay Session Details\n`;
        contextStr += `- **Recording Name**: ${selectedRecording.name}\n`;
        contextStr += `- **NORAD CATID / Target**: ${selectedRecording.norad_id}\n`;
        contextStr += `- **Recording Date/Time**: ${selectedRecording.timestamp}\n`;
        contextStr += `- **Total Recorded Data Points**: ${selectedRecording.scores ? selectedRecording.scores.length : 0}\n`;
        contextStr += `- **Playback Status**: Position ${activeData?.total_windows || 1} of ${selectedRecording.scores ? selectedRecording.scores.length : 0}\n`;
        
        if (selectedRecording.scores && selectedRecording.scores.length > 0) {
          const avgScore = selectedRecording.scores.reduce((a, b) => a + b, 0) / selectedRecording.scores.length;
          const maxScore = Math.max(...selectedRecording.scores);
          const maxIndex = selectedRecording.scores.indexOf(maxScore);
          const maxMeta = selectedRecording.metadata && selectedRecording.metadata[maxIndex];
          const maxTime = maxMeta ? new Date(maxMeta.timestamp * 1000).toLocaleString() : `Frame ${maxIndex + 1}`;
          
          const threshold = selectedRecording.threshold || 0.15;
          const anomalyCount = selectedRecording.scores.filter(s => s > threshold).length;
          
          contextStr += `- **Recording Average Anomaly Score**: ${avgScore.toFixed(4)}\n`;
          contextStr += `- **Recording Maximum Anomaly Score**: ${maxScore.toFixed(4)} (Occurred at: ${maxTime})\n`;
          contextStr += `- **Total Flagged Anomalies in Recording**: ${anomalyCount} (Threshold: ${threshold})\n`;
          
          const anomalies = [];
          selectedRecording.scores.forEach((score, i) => {
            if (score > threshold) {
              const meta = selectedRecording.metadata && selectedRecording.metadata[i];
              anomalies.push({
                frame: i + 1,
                timestamp: meta ? new Date(meta.timestamp * 1000).toLocaleString() : `Frame ${i + 1}`,
                score: score.toFixed(4),
                type: meta?.anomaly_type || "General Anomaly",
                battery_charge: meta?.battery_charge,
                battery_temp: meta?.battery_temp,
                solar_current: meta?.solar_current,
                comm_strength: meta?.comm_strength,
                cpu_load: meta?.cpu_load,
                wheel_speed_x: meta?.wheel_speed_x
              });
            }
          });
          
          if (anomalies.length > 0) {
            contextStr += `\n#### Recorded Anomalous Events Log\n`;
            contextStr += `| Frame | Timestamp | Anomaly Score | Flagged Subsystem / Parameter Values |\n`;
            contextStr += `| :--- | :--- | :--- | :--- |\n`;
            anomalies.slice(0, 30).forEach(anom => {
              const detailStr = `Type: **${anom.type}** | Batt: ${anom.battery_charge}% | Temp: ${anom.battery_temp}°C | Solar: ${anom.solar_current}A | Comm: ${anom.comm_strength}% | CPU: ${anom.cpu_load}% | Wheel: ${anom.wheel_speed_x} RPM`;
              contextStr += `| ${anom.frame} | ${anom.timestamp} | ${anom.score} | ${detailStr} |\n`;
            });
            if (anomalies.length > 30) {
              contextStr += `| ... | ... | ... | [Truncated ${anomalies.length - 30} further events for efficiency] |\n`;
            }
          } else {
            contextStr += `\n- **Anomaly Log**: No anomalous events were recorded in this session (all scores remained below threshold).\n`;
          }
        }
      } else if (activeData) {
        contextStr += `- **Analyzed Data Windows**: ${activeData.total_windows || 0}\n`;
        contextStr += `- **Subsystem Anomalies Flagged**: ${activeData.anomaly_count || 0}\n`;
        
        const metadataList = activeData.telemetryMetadata || [];
        const latestFrame = metadataList.length > 0 ? metadataList[metadataList.length - 1] : null;
        if (latestFrame) {
          contextStr += `\n#### Latest Real-Time Subsystem Frame Metrics (Timestamp: ${latestFrame.timestamp || "N/A"})\n`;
          contextStr += `| Subsystem Parameter | Current Telemetry Value |\n`;
          contextStr += `| :--- | :--- |\n`;
          contextStr += `| Satellite Lat/Lng | ${latestFrame.lat !== undefined ? latestFrame.lat + '°' : 'N/A'}, ${latestFrame.lng !== undefined ? latestFrame.lng + '°' : 'N/A'} |\n`;
          contextStr += `| Satellite Altitude | ${latestFrame.alt !== undefined ? latestFrame.alt + ' km' : 'N/A'} |\n`;
          contextStr += `| Eclipse / Sunlight State | ${latestFrame.sunlight || 'N/A'} |\n`;
          contextStr += `| Battery Charge Level | ${latestFrame.battery_charge !== undefined ? latestFrame.battery_charge + '%' : 'N/A'} |\n`;
          contextStr += `| Battery Operational Temp | ${latestFrame.battery_temp !== undefined ? latestFrame.battery_temp + '°C' : 'N/A'} |\n`;
          contextStr += `| Solar Array Output Current | ${latestFrame.solar_current !== undefined ? latestFrame.solar_current + ' A' : 'N/A'} |\n`;
          contextStr += `| Communication Link Strength | ${latestFrame.comm_strength !== undefined ? latestFrame.comm_strength + '%' : 'N/A'} |\n`;
          contextStr += `| Reaction Wheel Speed X | ${latestFrame.wheel_speed_x !== undefined ? latestFrame.wheel_speed_x + ' RPM' : 'N/A'} |\n`;
          contextStr += `| Spacecraft CPU Load | ${latestFrame.cpu_load !== undefined ? latestFrame.cpu_load + '%' : 'N/A'} |\n`;
          if (latestFrame.anomaly_type) {
            contextStr += `| Active Failure Flags | **${latestFrame.anomaly_type}** |\n`;
          }
        }
      }
    } else {
      contextStr += `\n- **Active Session**: No active live telemetry streaming session is currently active.\n`;
    }

    contextStr += `\n### Recent Flagged Subsystem Incidents\n`;
    if (recentAlerts && recentAlerts.length > 0) {
      contextStr += `| Alert ID | Channel | Severity | Max Score | Timestamp | Summary |\n`;
      contextStr += `| :--- | :--- | :--- | :--- | :--- | :--- |\n`;
      recentAlerts.slice(0, 8).forEach(alert => {
        const summary = alert.report ? (alert.report.split("\n")[0] || "").replace(/[^a-zA-Z0-9\s:]/g, "").substring(0, 80) : "No details";
        contextStr += `| ${alert.id} | ${alert.channel} | ${alert.severity} | ${alert.score.toFixed(4)} | ${alert.timestamp} | ${summary} |\n`;
      });
    } else {
      contextStr += `No active or recent telemetry incidents have been flagged in the current session.\n`;
    }

    return contextStr;
  };

  // General chat handler (sends normal text prompts to AI)
  const handleSendPrompt = async (customPrompt = null) => {
    const promptToSend = customPrompt || input.trim();
    if (!promptToSend || loading) return;

    if (!customPrompt) setInput("");


    
    const newMessages = [...messages, { role: "user", content: promptToSend }];
    setMessages(newMessages);
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // Send message history (display-only system greetings filtered out)
      const firstUserIndex = newMessages.findIndex(m => m.role === "user");
      const apiMessages = newMessages
        .slice(Math.max(firstUserIndex, 0))
        .map(m => ({ role: m.role, content: m.content }));

      const contextStr = serializeDashboardContext(activeTelemetry) + "\n\nUser is in the AI Space Analyst portal. They are asking questions about spacecraft health, dashboard telemetry, or querying orbital elements.";
      
      const lat = observerLat;
      const lng = observerLng;
      const alt = observerAlt;

      const res = await sendChatMessage(apiMessages, contextStr, activeModel, lat, lng, alt, controller.signal);
      
      setMessages([...newMessages, { role: "assistant", content: res.response }]);
    } catch (err) {
      if (
        err.name === "CanceledError" || 
        err.message === "canceled" || 
        err.code === "ERR_CANCELED" ||
        err.message?.includes("canceled") ||
        err.message?.includes("aborted")
      ) {
        setMessages([...newMessages, { 
          role: "assistant", 
          content: "*Inference cancelled by user.*"
        }]);
      } else {
        setMessages([...newMessages, { 
          role: "assistant", 
          content: err.message || "An unexpected error occurred while communicating with the AI service.",
          isError: true
        }]);
        setShowSettings(true); // Auto-expand settings on error
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setLoading(false);
    }
  };

  // Run CelesTrak Inference on the selected satellite constellation or NORAD ID
  const handleRunInference = async (mode, target) => {
    if (loading) return;
    
    const displayTarget = target.toUpperCase();
    const promptText = mode === "constellation" 
      ? `Run Anomaly Detection on the ${displayTarget} Constellation`
      : `Track and Analyze Telemetry Anomalies for NORAD Satellite #${displayTarget}`;
      
    const userMsg = { role: "user", content: promptText };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // Call Backend Celestrak Inference
      const result = await runCelestrakInfer(mode, target.toLowerCase(), controller.signal);
      
      // Build analysis summary text based on backend response
      const percentAnomalous = ((result.anomaly_count / result.total_windows) * 100).toFixed(1);
      const isHealthy = result.anomaly_count === 0;
      
      let summaryText = `**[Inference Completed Successfully]**\n\n`;
      summaryText += `I have fetched live elements from CelesTrak for **${displayTarget}** (${mode === "constellation" ? "Constellation Outliers" : "Single-Sat Epochs"}). `;
      summaryText += `I ran the telemetry parameters through our **TranAD Anomaly Detection** network running on the **${result.device.toUpperCase()}**.\n\n`;
      
      if (isHealthy) {
        summaryText += `✅ **System Status Nominal**: No anomalies were detected across the ${result.total_windows} telemetry points. All orbital parameters fall within acceptable margins.`;
      } else {
        summaryText += `⚠️ **Anomalies Detected**: I flagged **${result.anomaly_count}** anomalies out of ${result.total_windows} windows analyzed (**${percentAnomalous}%**). `;
        summaryText += `Detailed metrics are rendered below.`;
      }

      // Append assistant message with custom structured chart data
      const assistantMsg = {
        role: "assistant",
        content: summaryText,
        chartType: mode === "constellation" ? "bar" : "line",
        chartData: result.anomalies.map(a => ({
          name: mode === "constellation" ? a.metadata.name : a.metadata.epoch.substring(11, 16),
          score: a.score,
          norad_id: a.metadata.norad_id,
          anomaly: a.anomaly,
          epoch: a.metadata.epoch
        })),
        threshold: result.threshold,
        rawResult: result,
        summaryMetrics: {
          total: result.total_windows,
          anomalies: result.anomaly_count,
          device: result.device,
          threshold: result.threshold
        }
      };



      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      if (
        err.name === "CanceledError" || 
        err.message === "canceled" || 
        err.code === "ERR_CANCELED" ||
        err.message?.includes("canceled") ||
        err.message?.includes("aborted")
      ) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "*Inference cancelled by user.*"
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: `❌ **Inference Failed**: ${err.message}. Please check if the target is online and valid. CelesTrak might be offline or rate-limiting.`,
          isError: true
        }]);
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setLoading(false);
    }
  };

  // Export CSV Handler
  const handleExportCSV = async (msgIndex) => {
    const msg = messages[msgIndex];
    if (!msg || !msg.rawResult) return;

    try {
      const anomalies = msg.rawResult.anomalies;
      const headers = ["Index", "Name", "NORAD ID", "Epoch/ObjectID", "Anomaly Score", "Anomaly Flag"];
      
      const rows = anomalies.map(a => [
        a.index,
        a.metadata.name,
        a.metadata.norad_id,
        a.metadata.epoch !== "N/A" ? a.metadata.epoch : a.metadata.object_id,
        a.score,
        a.anomaly ? "TRUE" : "FALSE"
      ]);

      const blobData = await exportCSV(headers, rows);
      
      // Trigger browser download
      const url = window.URL.createObjectURL(new Blob([blobData]));
      const link = document.createElement('a');
      link.href = url;
      const safeTarget = (msg.rawResult.target || 'export').replace(/[^a-zA-Z0-9_-]/g, '_');
      link.setAttribute('download', `${safeTarget}_telemetry_report.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to export report: " + err.message);
    }
  };

  // Download Chart as SVG
  const downloadChart = (msgIndex) => {
    const container = chartRefs.current[msgIndex];
    if (!container) return;

    const svgElement = container.querySelector("svg");
    if (!svgElement) return;

    try {
      const serializer = new XMLSerializer();
      let source = serializer.serializeToString(svgElement);
      
      if (!source.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
        source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
      }
      if (!source.match(/^<svg[^>]+"http:\/\/www\.w3\.org\/1999\/xlink"/)) {
        source = source.replace(/^<svg/, '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
      }

      const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);
      const downloadLink = document.createElement("a");
      downloadLink.href = url;
      downloadLink.download = `STAD_chart_${msgIndex}.svg`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
    } catch (err) {
      alert("Failed to download chart: " + err.message);
    }
  };

  const starterPrompts = [
    { text: "Analyze NOAA weather satellite constellations for anomalies", icon: Sparkles, onClick: () => handleRunInference("constellation", "noaa") },
    { text: "Check ISS (ZARYA) historical orbital stability", icon: Database, onClick: () => handleRunInference("satellite", "25544") },
    { text: "Run outlier detection on GPS satellites", icon: FileText, onClick: () => handleRunInference("constellation", "gps-ops") },
    { text: "Fetch live telemetry elements for Starlink", icon: Activity, onClick: () => handleRunInference("constellation", "starlink") }
  ];

  return (
    <div className="chat-workspace-container" style={{ 
      display: "flex", 
      height: "calc(100% + 32px)", 
      width: "calc(100% + 64px)", 
      overflow: "hidden", 
      marginTop: "-32px", 
      marginBottom: 0,
      marginLeft: "-32px",
      marginRight: "-32px",
      padding: "32px 32px 0 32px", 
      boxSizing: "border-box", 
      position: "relative" 
    }}>
      <div className="chat-workspace" style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", paddingRight: 0 }}>
        {/* Settings bar inside Chat */}
        <div className="cyber-panel cyber-grid cyber-cyan" style={{ 
          padding: "10px 18px", 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "space-between", 
          marginBottom: 20,
          borderRadius: 6,
          borderLeft: "3px solid var(--primary)",
          boxShadow: "var(--glow-cyan)",
          background: "rgba(6, 6, 14, 0.95)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 10
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--success)", boxShadow: "0 0 6px var(--success)" }} className="animate-pulse" />
            <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-orbitron)", letterSpacing: "1px", color: "var(--primary)" }}>
              WORKSPACE AI ANALYTICS ENGINE // SESSION MEMORY ACTIVE
            </span>
          </div>
          
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {messages.length > 0 && (
              <button 
                onClick={handleClearHistory}
                className="btn"
                style={{ 
                  padding: "4px 10px", 
                  fontSize: 10, 
                  display: "flex", 
                  alignItems: "center", 
                  gap: 6,
                  height: 25,
                  borderRadius: 4,
                  background: "rgba(255, 51, 102, 0.05)",
                  borderColor: "rgba(255, 51, 102, 0.25)",
                  color: "var(--critical)",
                  fontFamily: "var(--font-orbitron)",
                  fontWeight: 700
                }}
                title="Clear Chat History"
              >
                <Trash2 size={11} /> CLEAR CHAT
              </button>
            )}
            <button 
              id="ai-preferences-toggle-btn"
              onClick={() => setShowSettings(!showSettings)}
              className="btn"
              style={{ 
                padding: "4px 10px", 
                fontSize: 10, 
                display: "flex", 
                alignItems: "center", 
                gap: 6,
                height: 25,
                borderRadius: 4,
                background: showSettings ? "rgba(0, 229, 255, 0.15)" : "rgba(255,255,255,0.03)",
                borderColor: showSettings ? "var(--primary)" : "rgba(0, 229, 255, 0.2)",
                color: showSettings ? "var(--primary)" : "var(--text-muted)",
                fontFamily: "var(--font-orbitron)",
                fontWeight: 700
              }}
              title="Toggle AI Preferences Panel"
            >
              <Settings size={11} /> PREFERENCES
            </button>
          </div>
        </div>

        {/* Main Messages View */}
        <div className="scroll-container" style={{ flex: 1, overflowY: "auto", paddingBottom: 24, paddingRight: 8 }}>
          {messages.length === 0 ? (
            /* Gemini style Greeting Welcome State */
            <div style={{ textAlign: "center", padding: "40px 20px" }}>
              <h1 className="gemini-gradient-text" style={{ fontSize: 42, fontWeight: 700, marginBottom: 8, letterSpacing: "-1px" }}>
                Hello, Space Engineer
              </h1>
              <p style={{ color: "var(--text-muted)", fontSize: 15, marginBottom: 40, fontWeight: 300 }}>
                How can I help you analyze satellite telemetry and detect anomalies today?
              </p>

              {/* Quick Suggestions Cards */}
              <div className="prompt-suggestions-grid">
                {starterPrompts.map((card, idx) => (
                  <button key={idx} className="prompt-card" onClick={card.onClick}>
                    <div className="prompt-card-text">{card.text}</div>
                    <div style={{ display: "flex", justifyContent: "flex-end", width: "100%", marginTop: 8 }}>
                      <card.icon className="prompt-card-icon" size={16} />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Messages Timeline */
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              {messages.map((msg, idx) => (
                <div key={idx} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {/* User Message */}
                  {msg.role === "user" && (
                    <div className="chat-bubble-user animate-slide-in" style={{ position: "relative", paddingRight: "40px" }}>
                      <button
                        onClick={() => handleCopyText(msg.content, idx)}
                        style={{
                          position: "absolute",
                          right: 8,
                          top: 8,
                          background: "transparent",
                          border: "none",
                          color: copiedIdx === idx ? "var(--success)" : "rgba(255,255,255,0.3)",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: 4,
                          borderRadius: 4,
                          transition: "color 0.2s"
                        }}
                        title="Copy message"
                      >
                        {copiedIdx === idx ? <CheckCircle size={14} /> : <Copy size={14} />}
                      </button>
                      {msg.content}
                    </div>
                  )}

                  {/* Assistant Message */}
                  {msg.role === "assistant" && (
                    <div className="chat-bubble-assistant animate-slide-in" style={{ position: "relative", paddingRight: "40px", borderColor: msg.isError ? "var(--critical)" : "rgba(0, 229, 255, 0.08)" }}>
                      <button
                        onClick={() => handleCopyText(msg.content, idx)}
                        style={{
                          position: "absolute",
                          right: 12,
                          top: 12,
                          background: "rgba(255, 255, 255, 0.02)",
                          border: "1px solid rgba(255, 255, 255, 0.05)",
                          color: copiedIdx === idx ? "var(--success)" : "rgba(255,255,255,0.4)",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: 6,
                          borderRadius: 6,
                          transition: "all 0.2s"
                        }}
                        title="Copy response"
                      >
                        {copiedIdx === idx ? <CheckCircle size={14} /> : <Copy size={14} />}
                      </button>
                      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                        <div style={{ 
                          width: 32, height: 32, borderRadius: "50%", 
                          background: msg.isError ? "rgba(255, 51, 102, 0.15)" : "var(--primary-dim)",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          color: msg.isError ? "var(--critical)" : "var(--primary)",
                          flexShrink: 0
                        }}>
                          <Cpu size={16} />
                        </div>
                        <div style={{ flex: 1, fontSize: 14 }}>
                          {/* Format Markdown code blocks and linebreaks */}
                          <div 
                            dangerouslySetInnerHTML={{ __html: sanitizeHTML(parseMarkdownToHTML(msg.content)) }} 
                            style={{ color: "#e0e0e0", fontSize: "13.5px", lineHeight: "1.6" }}
                          />

                          {/* Summary Metrics Display */}
                          {msg.summaryMetrics && (
                            <div style={{ 
                              display: "grid", 
                              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", 
                              gap: 12, 
                              marginTop: 20 
                            }}>
                              <div className="glass-panel" style={{ padding: 12, background: "rgba(0,0,0,0.2)" }}>
                                <div style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase" }}>Total Telemetry Points</div>
                                <div style={{ fontSize: 18, fontWeight: 600, color: "#fff" }}>{msg.summaryMetrics.total}</div>
                              </div>
                              <div className="glass-panel" style={{ padding: 12, background: "rgba(0,0,0,0.2)" }}>
                                <div style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase" }}>Anomalies Flagged</div>
                                <div style={{ 
                                  fontSize: 18, 
                                  fontWeight: 600, 
                                  color: msg.summaryMetrics.anomalies > 0 ? "var(--critical)" : "var(--success)" 
                                }}>
                                  {msg.summaryMetrics.anomalies}
                                </div>
                              </div>
                              <div className="glass-panel" style={{ padding: 12, background: "rgba(0,0,0,0.2)" }}>
                                <div style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase" }}>Detection Threshold</div>
                                <div style={{ fontSize: 18, fontWeight: 600, color: "var(--medium)" }}>{msg.summaryMetrics.threshold.toFixed(3)}</div>
                              </div>
                            </div>
                          )}

                          {/* Interactive Recharts Chart inside Bubble */}
                          {msg.chartData && (
                            <div className="inline-chart-panel" ref={el => chartRefs.current[idx] = el}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                                <div style={{ fontSize: 12, fontWeight: 600, color: "#fff", display: "flex", alignItems: "center", gap: 6 }}>
                                  <Activity size={14} color="var(--primary)" />
                                  Anomaly Score Distribution (Live Celestrak Telemetry)
                                </div>
                                <div style={{ display: "flex", gap: 8 }}>
                                  <button className="btn" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => downloadChart(idx)}>
                                    <Download size={12} /> Save Chart (SVG)
                                  </button>
                                  <button className="btn btn-primary" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => handleExportCSV(idx)}>
                                    <FileText size={12} /> Export Excel (CSV)
                                  </button>
                                </div>
                              </div>
                              
                              <div style={{ height: 220, width: "100%" }}>
                                <ResponsiveContainer width="100%" height="100%">
                                  {msg.chartType === "bar" ? (
                                    <BarChart data={msg.chartData}>
                                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                      <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} />
                                      <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} />
                                      <Tooltip 
                                        contentStyle={{ background: "rgba(10, 10, 20, 0.95)", border: "1px solid var(--border-glow)", color: "#fff" }}
                                        labelFormatter={(val) => `Satellite: ${val}`}
                                      />
                                      <ReferenceLine y={msg.threshold} stroke="var(--critical)" strokeDasharray="5 5" label={{ value: "Threshold", fill: "var(--critical)", fontSize: 9, position: "top" }} />
                                      <Bar dataKey="score">
                                        {msg.chartData.map((entry, index) => (
                                          <Cell 
                                            key={`cell-${index}`} 
                                            fill={entry.anomaly ? "var(--critical)" : "var(--primary)"} 
                                          />
                                        ))}
                                      </Bar>
                                    </BarChart>
                                  ) : (
                                    <LineChart data={msg.chartData}>
                                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                      <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={10} tickLine={false} />
                                      <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} />
                                      <Tooltip 
                                        contentStyle={{ background: "rgba(10, 10, 20, 0.95)", border: "1px solid var(--border-glow)", color: "#fff" }}
                                        labelFormatter={(val) => `Time Index: ${val}`}
                                      />
                                      <ReferenceLine y={msg.threshold} stroke="var(--critical)" strokeDasharray="5 5" label={{ value: "Threshold", fill: "var(--critical)", fontSize: 9, position: "top" }} />
                                      <Line 
                                        type="monotone" 
                                        dataKey="score" 
                                        stroke="var(--primary)" 
                                        strokeWidth={2}
                                        dot={(props) => {
                                          const { cx, cy, payload } = props;
                                          if (payload.anomaly) {
                                            return <circle cx={cx} cy={cy} r={5} fill="var(--critical)" stroke="none" />;
                                          }
                                          return <circle cx={cx} cy={cy} r={2} fill="var(--primary)" stroke="none" />;
                                        }}
                                      />
                                    </LineChart>
                                  )}
                                </ResponsiveContainer>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="chat-bubble-assistant animate-pulse" style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <Cpu size={16} className="animate-spin" color="var(--primary)" />
                  <span style={{ fontSize: 13, color: "var(--primary)" }}>Processing telemetry streams... executing TranAD multi-variate anomaly detection core...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Dynamic API Configuration Drawer & Prompt Input Area */}
        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
          
          {/* API Selector Panel / Telemetry Controller */}
          <div className="cyber-panel cyber-grid cyber-cyan" style={{ 
            padding: "10px 18px", 
            borderRadius: 6, 
            display: "flex", 
            flexWrap: "wrap",
            alignItems: "center", 
            justifyContent: "space-between",
            gap: 12,
            background: "rgba(3, 3, 7, 0.75)",
            borderLeft: "3px solid var(--primary)",
            boxShadow: "var(--glow-cyan)",
            position: "relative"
          }}>
            <div className="scanner-line"></div>
            <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "var(--font-orbitron)", fontWeight: 700, letterSpacing: "0.5px" }}>TRACKING MODE:</span>
                <div style={{ display: "flex", background: "rgba(0,0,0,0.5)", borderRadius: 4, padding: 2, border: "1px solid rgba(0, 229, 255, 0.2)" }}>
                  <button 
                    onClick={() => { setTrackingMode("constellation"); setTargetName("noaa"); }}
                    style={{
                      background: trackingMode === "constellation" ? "rgba(0, 229, 255, 0.15)" : "transparent",
                      color: trackingMode === "constellation" ? "var(--primary)" : "var(--text-muted)",
                      border: "none", borderRadius: 3, padding: "4px 10px", fontSize: 10, cursor: "pointer", transition: "all 0.2s",
                      fontFamily: "var(--font-orbitron)", fontWeight: 600
                    }}
                  >
                    CONSTELLATION OUTLIERS
                  </button>
                  <button 
                    onClick={() => { setTrackingMode("satellite"); setTargetName("25544"); }}
                    style={{
                      background: trackingMode === "satellite" ? "rgba(0, 229, 255, 0.15)" : "transparent",
                      color: trackingMode === "satellite" ? "var(--primary)" : "var(--text-muted)",
                      border: "none", borderRadius: 3, padding: "4px 10px", fontSize: 10, cursor: "pointer", transition: "all 0.2s",
                      fontFamily: "var(--font-orbitron)", fontWeight: 600
                    }}
                  >
                    SINGLE SAT TIMELINE
                  </button>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "var(--font-orbitron)", fontWeight: 700, letterSpacing: "0.5px" }}>TARGET CONFIG:</span>
                {trackingMode === "constellation" ? (
                  <select 
                    value={targetName} 
                    onChange={(e) => setTargetName(e.target.value)}
                    style={{
                      background: "rgba(5, 5, 10, 0.9)",
                      border: "1px solid rgba(0, 229, 255, 0.3)",
                      borderRadius: 4,
                      color: "#fff",
                      fontSize: 11,
                      padding: "5px 10px",
                      outline: "none",
                      cursor: "pointer",
                      fontFamily: "var(--font-orbitron)",
                      fontWeight: 600
                    }}
                  >
                    <option value="noaa">NOAA WEATHER SATELLITES</option>
                    <option value="starlink">STARLINK CONSTELLATION</option>
                    <option value="gps-ops">GPS OPERATIONS</option>
                    <option value="weather">GENERAL WEATHER SATELLITES</option>
                    <option value="active">ACTIVE SATELLITE INDEX</option>
                  </select>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <input 
                      type="text" 
                      value={targetName} 
                      onChange={(e) => setTargetName(e.target.value)}
                      placeholder="NORAD ID"
                      style={{
                        width: 90,
                        background: "rgba(5, 5, 10, 0.9)",
                        border: "1px solid rgba(0, 229, 255, 0.3)",
                        borderRadius: 4,
                        color: "#fff",
                        fontSize: 11,
                        padding: "5px 8px",
                        outline: "none",
                        fontFamily: "var(--font-share-tech)",
                        textAlign: "center"
                      }}
                    />
                    <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "var(--font-share-tech)" }}>(e.g. 25544 = ISS)</span>
                  </div>
                )}
              </div>
            </div>

            <button 
              onClick={() => handleRunInference(trackingMode, targetName)}
              disabled={loading}
              className="btn btn-primary"
              style={{ 
                height: 28,
                padding: "0 14px", 
                fontSize: 10, 
                borderRadius: 4,
                fontFamily: "var(--font-orbitron)",
                fontWeight: 700,
                letterSpacing: "0.5px"
              }}
            >
              {loading ? <RefreshCw size={12} className="animate-spin" /> : <RefreshCw size={12} />} RUN ORBIT ANALYTICS
            </button>
          </div>

          {/* Input Bar */}
          <div className="gemini-input-wrapper">
            <MessageSquare size={16} color="var(--primary)" style={{ opacity: 0.6 }} />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendPrompt()}
              placeholder="Ask AI Space Analyst..."
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                color: "#fff",
                fontSize: 14,
                outline: "none",
                fontFamily: "var(--font-inter)"
              }}
            />
            <button 
              onClick={() => setShowImportModal(true)}
              disabled={loading}
              className="btn"
              style={{ 
                background: "transparent",
                border: "none",
                display: "flex", alignItems: "center", justifyContent: "center",
                padding: "0 8px",
                cursor: "pointer",
                color: "var(--primary)",
                opacity: 0.8,
                marginRight: 4
              }}
              title="Import and Normalize Report"
            >
              <Upload size={16} />
            </button>
            {loading ? (
              <button 
                onClick={handleCancelQuery}
                className="btn"
                style={{ 
                  width: 38, height: 38, borderRadius: "50%", 
                  display: "flex", alignItems: "center", justifyContent: "center",
                  padding: 0,
                  minWidth: 38,
                  flexShrink: 0,
                  background: "rgba(255, 51, 102, 0.15)",
                  borderColor: "var(--critical)",
                  color: "var(--critical)",
                  boxShadow: "0 0 10px rgba(255, 51, 102, 0.3)",
                  cursor: "pointer"
                }}
                title="Cancel Generation"
              >
                <X size={16} />
              </button>
            ) : (
              <button 
                onClick={() => handleSendPrompt()}
                disabled={!input.trim()}
                className="btn btn-primary"
                style={{ 
                  width: 38, height: 38, borderRadius: "50%", 
                  display: "flex", alignItems: "center", justifyContent: "center",
                  padding: 0,
                  minWidth: 38,
                  flexShrink: 0
                }}
              >
                <Send size={16} />
              </button>
            )}
          </div>
          <div style={{ textAlign: "center", fontSize: 10, color: "var(--text-muted)", paddingBottom: 16 }}>
            Live telemetry analyses rely on orbital parameters updated daily via the CelesTrak database.
          </div>
        </div>
      </div>

      {showSettings && (
        <div ref={settingsPanelRef} className="cyber-panel cyber-grid cyber-cyan" style={{
          position: "absolute",
          top: "84px",
          right: "32px",
          width: "340px",
          maxHeight: "calc(100% - 130px)",
          overflowY: "auto",
          padding: "20px",
          border: "1px solid rgba(0, 229, 255, 0.25)",
          borderLeft: "4px solid var(--primary)",
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.7), var(--glow-cyan)",
          background: "rgba(6, 6, 12, 0.95)",
          backdropFilter: "blur(20px)",
          borderRadius: 6,
          zIndex: 50,
          animation: "slide-in-right 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards"
        }}>
          <div className="scanner-line"></div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, borderBottom: "1px solid rgba(0,229,255,0.15)", paddingBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-orbitron)", color: "var(--primary)", letterSpacing: "1.5px" }}>AI PREFERENCES</span>
            <button 
              onClick={() => setShowSettings(false)}
              style={{
                background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center"
              }}
              title="Close Preferences"
              onMouseEnter={(e) => e.target.style.color = "var(--primary)"}
              onMouseLeave={(e) => e.target.style.color = "var(--text-muted)"}
            >
              <X size={14} />
            </button>
          </div>
          <AISettingsPanel 
            selectedModel={activeModel} 
            setSelectedModel={(model) => {
              setActiveModel(model);
              if (model) {
                localStorage.setItem("selectedModel", model);
              } else {
                localStorage.removeItem("selectedModel");
              }
            }}
            hideTelemetrySettings={false}
          />
        </div>
      )}

      {showImportModal && (
        <div style={{
          position: "fixed",
          top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0, 0, 0, 0.75)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 100
        }}>
          <div className="cyber-panel cyber-grid cyber-cyan" style={{
            width: "420px",
            padding: "24px",
            border: "1px solid rgba(0, 229, 255, 0.25)",
            borderLeft: "4px solid var(--primary)",
            background: "rgba(6, 6, 12, 0.95)",
            backdropFilter: "blur(20px)",
            borderRadius: 8,
            boxShadow: "0 10px 40px rgba(0,0,0,0.8), var(--glow-cyan)",
            position: "relative"
          }}>
            <div className="scanner-line"></div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <span style={{ fontSize: 13, fontWeight: 700, fontFamily: "var(--font-orbitron)", color: "var(--primary)", letterSpacing: "1.5px" }}>IMPORT & NORMALIZE REPORT</span>
              <button 
                onClick={() => setShowImportModal(false)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center" }}
              >
                <X size={16} />
              </button>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 11, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", fontWeight: 700 }}>Report Type</label>
                <select 
                  value={importReportType} 
                  onChange={(e) => setImportReportType(e.target.value)}
                  style={{
                    width: "100%",
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "8px 10px",
                    fontSize: "13px",
                    color: "#fff",
                    outline: "none"
                  }}
                >
                  <option value="Business Report">Business Report</option>
                  <option value="Research Report">Research Report</option>
                  <option value="Technical Report">Technical Report</option>
                  <option value="Audit Report">Audit Report</option>
                  <option value="Analytical Report">Analytical Report</option>
                  <option value="Project Documentation">Project Documentation</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", fontWeight: 700 }}>Custom Instructions (Optional)</label>
                <textarea
                  placeholder="e.g. Provide a highly detailed and elaborated output of the findings section."
                  value={importInstructions}
                  onChange={(e) => setImportInstructions(e.target.value)}
                  rows={3}
                  style={{
                    width: "100%",
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "8px 10px",
                    fontSize: "12px",
                    color: "#fff",
                    outline: "none",
                    resize: "none"
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 11, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", fontWeight: 700 }}>Select File (.txt, .md, .csv)</label>
                <input 
                  type="file" 
                  accept=".txt,.md,.csv,.json"
                  onChange={handleImportFileChange}
                  style={{ fontSize: "12px", color: "var(--text-muted)", width: "100%" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 8 }}>
                <button 
                  className="btn" 
                  onClick={() => setShowImportModal(false)}
                  style={{ fontSize: "11px", fontWeight: 700 }}
                >
                  Cancel
                </button>
                <button 
                  className="btn btn-primary" 
                  disabled={!importFile || loading}
                  onClick={handleRunImport}
                  style={{ fontSize: "11px", fontWeight: 700 }}
                >
                  Normalize & Import
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
