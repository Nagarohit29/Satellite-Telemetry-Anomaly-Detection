import React, { useState, useEffect } from "react";
import { getLLMModels, updateAPIKey, deleteAPIKey, getLocalOllamaConfig, updateLocalOllama, getKeysStatus } from "../api/endpoints";
import { Check, Edit2, Save, Trash2, Key, Loader2, RefreshCw, Monitor, Cloud, Sparkles, Satellite } from "lucide-react";

const CLOUD_MODELS_WITH_KEYS = ["ollama_cloud", "gemini", "openai", "anthropic"];

export default function AISettingsPanel({ selectedModel, setSelectedModel, onKeyStatusChange, hideModelSelection = false, hideTelemetrySettings = false }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingProvider, setEditingProvider] = useState(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [confirmingDelete, setConfirmingDelete] = useState(null);

  // Custom Local Ollama configs
  const [localModelName, setLocalModelName] = useState("");
  const [localApiBase, setLocalApiBase] = useState("");
  const [editingLocal, setEditingLocal] = useState(false);

  // N2YO Live telemetry config
  const [n2yoStatus, setN2yoStatus] = useState(false);
  const [n2yoKeyInput, setN2yoKeyInput] = useState("");
  const [editingN2yo, setEditingN2yo] = useState(false);

  // Observer ground station coordinates
  const [observerLat, setObserverLat] = useState(() => {
    return parseFloat(localStorage.getItem("observerLat")) || 0.0;
  });
  const [observerLng, setObserverLng] = useState(() => {
    return parseFloat(localStorage.getItem("observerLng")) || 0.0;
  });
  const [observerAlt, setObserverAlt] = useState(() => {
    return parseFloat(localStorage.getItem("observerAlt")) || 0.0;
  });

  // String states for ground observer coordinates to allow comfortable typing
  const [latInput, setLatInput] = useState(() => localStorage.getItem("observerLat") || "0.0");
  const [lngInput, setLngInput] = useState(() => localStorage.getItem("observerLng") || "0.0");
  const [altInput, setAltInput] = useState(() => localStorage.getItem("observerAlt") || "0.0");

  // Sync observer coordinates to localStorage
  useEffect(() => {
    localStorage.setItem("observerLat", observerLat.toString());
  }, [observerLat]);
  useEffect(() => {
    localStorage.setItem("observerLng", observerLng.toString());
  }, [observerLng]);
  useEffect(() => {
    localStorage.setItem("observerAlt", observerAlt.toString());
  }, [observerAlt]);

  const handleApplyObserver = () => {
    let parsedLat = parseFloat(latInput);
    let parsedLng = parseFloat(lngInput);
    let parsedAlt = parseFloat(altInput);

    if (isNaN(parsedLat)) parsedLat = 0.0;
    if (isNaN(parsedLng)) parsedLng = 0.0;
    if (isNaN(parsedAlt)) parsedAlt = 0.0;

    const clampedLat = Math.max(-90.0, Math.min(90.0, parsedLat));
    const clampedLng = Math.max(-180.0, Math.min(180.0, parsedLng));
    const clampedAlt = Math.max(0.0, Math.min(100000.0, parsedAlt));

    setLatInput(clampedLat.toString());
    setLngInput(clampedLng.toString());
    setAltInput(clampedAlt.toString());

    setObserverLat(clampedLat);
    setObserverLng(clampedLng);
    setObserverAlt(clampedAlt);

    localStorage.setItem("observerLat", clampedLat.toString());
    localStorage.setItem("observerLng", clampedLng.toString());
    localStorage.setItem("observerAlt", clampedAlt.toString());
  };

  useEffect(() => {
    fetchModels();
    fetchLocalOllamaConfig();
    fetchKeysStatus();
    setSaveStatus(null);
    setEditingLocal(false);
    setEditingProvider(null);
    setEditingN2yo(false);
  }, []);

  const fetchKeysStatus = async () => {
    try {
      const data = await getKeysStatus();
      setN2yoStatus(data.n2yo || false);
    } catch (err) {
      console.error("Failed to load keys status:", err);
    }
  };

  const fetchLocalOllamaConfig = async () => {
    try {
      const data = await getLocalOllamaConfig();
      setLocalModelName(data.model || "llama3.2");
      setLocalApiBase(data.api_base || "http://localhost:11434");
    } catch (err) {
      console.error("Failed to load local Ollama config:", err);
    }
  };

  const fetchModels = async () => {
    try {
      setLoading(true);
      const data = await getLLMModels();
      const nextModels = data.models || [];
      setModels(nextModels);

      const selectedConfig = nextModels.find((model) => model.id === selectedModel);
      if (selectedModel && selectedConfig && !selectedConfig.available) {
        setSelectedModel("");
        localStorage.removeItem("selectedModel");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveKey = async (provider) => {
    const key = apiKeyInput.trim();
    if (!key) return;

    if (!["ollama_cloud", "ollama"].includes(provider) && key.length < 20) {
      setSaveStatus({ type: "error", msg: "API key looks too short. Please paste a valid key." });
      return;
    }

    try {
      setIsSaving(true);
      setSaveStatus(null);
      await updateAPIKey(provider, key, true);
      setEditingProvider(null);
      setApiKeyInput("");
      setSaveStatus({ type: "success", msg: `${provider} key saved successfully.` });
      await fetchModels();
    } catch (err) {
      setSaveStatus({ type: "error", msg: err.message || "Failed to save key" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteKey = async (provider) => {
    try {
      setIsSaving(true);
      setSaveStatus(null);
      setConfirmingDelete(null);
      await deleteAPIKey(provider);
      setEditingProvider(null);
      setApiKeyInput("");
      setSaveStatus({ type: "success", msg: `${provider} key removed.` });
      if (selectedModel === provider) {
        setSelectedModel("");
        localStorage.removeItem("selectedModel");
      }
      await fetchModels();
    } catch (err) {
      setSaveStatus({ type: "error", msg: err.message || "Failed to delete key" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveLocalConfig = async () => {
    try {
      setIsSaving(true);
      setSaveStatus(null);
      await updateLocalOllama(localModelName, localApiBase, true);
      setEditingLocal(false);
      setSaveStatus({ type: "success", msg: "Local Ollama settings updated and verified." });
      await fetchModels();
    } catch (err) {
      setSaveStatus({ type: "error", msg: err.message || "Failed to save Local Ollama config" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveN2yoKey = async () => {
    const key = n2yoKeyInput.trim();
    if (!key) return;

    try {
      setIsSaving(true);
      setSaveStatus(null);
      await updateAPIKey("n2yo", key, true);
      setEditingN2yo(false);
      setN2yoKeyInput("");
      setSaveStatus({ type: "success", msg: "N2YO API key saved successfully." });
      // Optimistically update status — the save succeeded, so the key is now active
      setN2yoStatus(true);
      // Also refresh from server to confirm (non-blocking)
      fetchKeysStatus();
      if (onKeyStatusChange) onKeyStatusChange();
    } catch (err) {
      setSaveStatus({ type: "error", msg: err.message || "Failed to save N2YO key" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteN2yoKey = async () => {
    try {
      setIsSaving(true);
      setSaveStatus(null);
      await deleteAPIKey("n2yo");
      setEditingN2yo(false);
      setN2yoKeyInput("");
      setSaveStatus({ type: "success", msg: "N2YO API key removed." });
      await fetchKeysStatus();
      if (onKeyStatusChange) onKeyStatusChange();
    } catch (err) {
      setSaveStatus({ type: "error", msg: err.message || "Failed to delete N2YO key" });
    } finally {
      setIsSaving(false);
    }
  };

  const needsApiKey = (modelId) => CLOUD_MODELS_WITH_KEYS.includes(modelId);

  const getStatusText = (model) => {
    if (selectedModel === model.id && model.available && model.ready !== false) return "CURRENTLY ACTIVE";
    if (model.status_text) return model.status_text;
    if (model.available) return "AVAILABLE - CLICK TO SELECT";
    if (model.type === "device") return "SERVER NOT RUNNING";
    return "MISSING API KEY";
  };

  const deviceModels = models.filter((m) => m.type === "device");
  const cloudModels = models.filter((m) => m.type === "cloud");

  return (
    <div className="chat-settings-sidebar-content" style={{ display: "flex", flexDirection: "column", height: "100%", overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 600, color: "#fff" }}>
          {hideModelSelection ? (
            <>
              <Satellite size={16} color="var(--primary)" />
              Telemetry Preferences
            </>
          ) : (
            <>
              <Sparkles size={16} color="var(--primary)" />
              AI Preferences
            </>
          )}
        </div>
        {!hideModelSelection && (
          <button
            onClick={() => {
              setSaveStatus(null);
              fetchModels();
            }}
            className="btn"
            style={{ padding: "4px", background: "transparent", border: "1px solid var(--border-color)", borderRadius: "6px" }}
            title="Refresh model status"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        )}
      </div>

      {saveStatus && (
        <div
          style={{
            padding: "8px 12px",
            marginBottom: "16px",
            borderRadius: "8px",
            fontSize: "11px",
            fontWeight: 500,
            background: saveStatus.type === "success" ? "rgba(0,255,136,0.1)" : "rgba(255,51,102,0.1)",
            border: `1px solid ${saveStatus.type === "success" ? "var(--success)" : "var(--critical)"}`,
            color: saveStatus.type === "success" ? "var(--success)" : "var(--critical)",
          }}
        >
          {saveStatus.msg}
        </div>
      )}

      {!hideModelSelection && (
        <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            marginBottom: "12px",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
          }}
        >
          Engine Selection
        </div>

        <div
          style={{
            padding: "8px 12px",
            marginBottom: "12px",
            borderRadius: "8px",
            fontSize: "11px",
            background: "rgba(255,255,255,0.04)",
            border: "1px solid var(--border-color)",
            color: "var(--text-muted)",
          }}
        >
          API keys entered here are session-only by default and are not written to disk.
        </div>

        {!selectedModel && !loading && (
          <div
            style={{
              padding: "8px 12px",
              marginBottom: "12px",
              borderRadius: "8px",
              fontSize: "11px",
              background: "rgba(0,200,255,0.08)",
              border: "1px solid var(--primary-dim)",
              color: "var(--primary)",
              display: "flex",
              alignItems: "flex-start",
              gap: 8,
            }}
          >
            <span style={{ fontSize: "11px", fontWeight: 700, background: "var(--primary)", color: "#000", padding: "1px 4px", borderRadius: 4, lineHeight: "1", marginTop: 1 }}>AUTO</span>
            <span>
              <strong>Auto Fallback</strong> - If Local Ollama is online, it is used by default. Select a cloud engine to override.
            </span>
          </div>
        )}

        {loading ? (
          <div className="model-list" style={{ gap: 8 }}>
            <div
              style={{
                fontSize: "10px",
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <Loader2 className="animate-spin" size={10} color="var(--primary)" /> Loading engines...
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton skeleton-card" style={{ height: 50, animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
        ) : error ? (
          <div
            style={{
              padding: "12px",
              background: "rgba(255, 51, 102, 0.1)",
              border: "1px solid var(--critical)",
              borderRadius: "8px",
              color: "var(--critical)",
              fontSize: "12px",
            }}
          >
            {error}
          </div>
        ) : (
          <div className="model-list" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {deviceModels.length > 0 && (
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginBottom: "4px",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Monitor size={10} /> Device
              </div>
            )}

            {deviceModels.map((model) => (
              <div key={model.id} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div
                  className={`model-card ${selectedModel === model.id ? "selected" : ""} ${!model.available && !editingLocal ? "disabled" : ""}`}
                  onClick={() => {
                    if (model.available) {
                      if (selectedModel === model.id) {
                        setSelectedModel("");
                        localStorage.removeItem("selectedModel");
                      } else {
                        setSelectedModel(model.id);
                      }
                    } else if (!editingLocal) {
                      setEditingLocal(true);
                    }
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "10px 12px",
                    background: selectedModel === model.id ? "var(--primary-dim)" : "rgba(255,255,255,0.02)",
                    border: "1px solid",
                    borderColor: selectedModel === model.id ? "var(--primary)" : "var(--border-color)",
                    borderRadius: 8,
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                >
                  <div className="selection-indicator" style={{
                    width: 14, height: 14, borderRadius: "50%", border: "1px solid var(--border-color)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: selectedModel === model.id ? "var(--primary)" : "transparent"
                  }}>
                    {selectedModel === model.id && <Check size={8} color="#000" strokeWidth={3} />}
                  </div>
                  <div className="model-info" style={{ flex: 1 }}>
                    <div className="model-name" style={{ fontSize: 12, fontWeight: 500, color: "#fff" }}>{model.name}</div>
                    <div className="model-status" style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2 }}>{getStatusText(model)}</div>
                  </div>
                  <button
                    className="btn"
                    style={{ padding: "4px", opacity: 0.6 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingLocal(!editingLocal);
                    }}
                  >
                    <Edit2 size={12} />
                  </button>
                </div>

                {editingLocal && (
                  <div className="glass-panel" style={{ padding: "12px", borderRadius: "10px", border: "1px solid var(--primary-dim)", display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 500 }}>Configure Local Ollama:</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <input
                        type="text"
                        placeholder="Endpoint URL"
                        value={localApiBase}
                        onChange={(e) => setLocalApiBase(e.target.value)}
                        style={{
                          background: "rgba(0,0,0,0.3)",
                          border: "1px solid var(--border-color)",
                          borderRadius: "6px",
                          padding: "6px 10px",
                          fontSize: "12px",
                          color: "#fff",
                          outline: "none"
                        }}
                      />
                      <input
                        type="text"
                        placeholder="Engine Name"
                        value={localModelName}
                        onChange={(e) => setLocalModelName(e.target.value)}
                        style={{
                          background: "rgba(0,0,0,0.3)",
                          border: "1px solid var(--border-color)",
                          borderRadius: "6px",
                          padding: "6px 10px",
                          fontSize: "12px",
                          color: "#fff",
                          outline: "none"
                        }}
                      />
                    </div>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
                      <button
                        className="btn btn-primary"
                        style={{ padding: "4px 8px", fontSize: "11px" }}
                        disabled={isSaving}
                        onClick={handleSaveLocalConfig}
                      >
                        <Save size={12} /> Save Config
                      </button>
                      <button
                        className="btn"
                        style={{ padding: "4px 8px", fontSize: "11px" }}
                        onClick={() => setEditingLocal(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {cloudModels.length > 0 && (
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginTop: "8px",
                  marginBottom: "4px",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Cloud size={10} /> Cloud API
              </div>
            )}

            {cloudModels.map((model) => (
              <div key={model.id} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div
                  className={`model-card ${selectedModel === model.id ? "selected" : ""} ${!model.available && editingProvider !== model.id ? "disabled" : ""}`}
                  onClick={() => {
                    if (model.available) {
                      if (selectedModel === model.id) {
                        setSelectedModel("");
                        localStorage.removeItem("selectedModel");
                      } else {
                        setSelectedModel(model.id);
                      }
                    } else if (editingProvider !== model.id) {
                      setEditingProvider(model.id);
                    }
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "10px 12px",
                    background: selectedModel === model.id ? "var(--primary-dim)" : "rgba(255,255,255,0.02)",
                    border: "1px solid",
                    borderColor: selectedModel === model.id ? "var(--primary)" : "var(--border-color)",
                    borderRadius: 8,
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                >
                  <div className="selection-indicator" style={{
                    width: 14, height: 14, borderRadius: "50%", border: "1px solid var(--border-color)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: selectedModel === model.id ? "var(--primary)" : "transparent"
                  }}>
                    {selectedModel === model.id && <Check size={8} color="#000" strokeWidth={3} />}
                  </div>
                  <div className="model-info" style={{ flex: 1 }}>
                    <div className="model-name" style={{ fontSize: 12, fontWeight: 500, color: "#fff" }}>{model.name}</div>
                    <div className="model-status" style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2 }}>{getStatusText(model)}</div>
                  </div>
                  {needsApiKey(model.id) && (
                    <button
                      className="btn"
                      style={{ padding: "4px", opacity: 0.6 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (editingProvider === model.id) {
                          setEditingProvider(null);
                          setApiKeyInput("");
                        } else {
                          setEditingProvider(model.id);
                          setApiKeyInput("");
                        }
                      }}
                    >
                      <Edit2 size={12} />
                    </button>
                  )}
                </div>

                {editingProvider === model.id && (
                  <div className="glass-panel" style={{ padding: "10px", borderRadius: "10px", border: "1px solid var(--primary-dim)" }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <div style={{ flex: 1, position: "relative" }}>
                        <Key size={12} style={{ position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)", opacity: 0.5 }} />
                        <input
                          type="password"
                          placeholder="Enter API Key"
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && apiKeyInput.trim()) {
                              handleSaveKey(model.id);
                            }
                          }}
                          style={{
                            width: "100%",
                            background: "rgba(0,0,0,0.3)",
                            border: "1px solid var(--border-color)",
                            borderRadius: "6px",
                            padding: "6px 8px 6px 28px",
                            fontSize: "12px",
                            color: "#fff",
                            outline: "none",
                          }}
                          autoFocus
                        />
                      </div>
                      <button
                        className="btn btn-primary"
                        style={{ padding: "6px" }}
                        disabled={isSaving || !apiKeyInput.trim()}
                        onClick={() => handleSaveKey(model.id)}
                      >
                        <Save size={14} />
                      </button>
                      {confirmingDelete === model.id ? (
                        <>
                          <button
                            className="btn btn-primary"
                            style={{ padding: "4px 8px", fontSize: "10px", background: "var(--critical)", border: "1px solid var(--critical)" }}
                            disabled={isSaving}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteKey(model.id);
                            }}
                          >
                            Confirm
                          </button>
                          <button
                            className="btn"
                            style={{ padding: "4px 8px", fontSize: "10px" }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmingDelete(null);
                            }}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          className="btn"
                          style={{ padding: "6px", color: "var(--critical)" }}
                          disabled={isSaving}
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmingDelete(model.id);
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {/* Telemetry Integration Section */}
      {!hideTelemetrySettings && (
        <div style={{ marginTop: hideModelSelection ? "0px" : "24px", paddingTop: hideModelSelection ? "0px" : "20px", borderTop: hideModelSelection ? "none" : "1px solid var(--border-color)", marginBottom: "16px" }}>
          <div
            style={{
              fontSize: "11px",
              color: "var(--text-muted)",
              marginBottom: "12px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              display: "flex",
              alignItems: "center",
              gap: 6
            }}
          >
            <Satellite size={12} color="var(--primary)" /> Telemetry API & Observer
          </div>

          {/* N2YO Key Config */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: "16px" }}>
            <div
              className={`model-card ${n2yoStatus ? "selected" : ""}`}
              onClick={() => {
                if (!n2yoStatus) {
                  setEditingN2yo(true);
                }
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "10px 12px",
                background: n2yoStatus ? "var(--primary-dim)" : "rgba(255,255,255,0.02)",
                border: "1px solid",
                borderColor: n2yoStatus ? "var(--primary)" : "var(--border-color)",
                borderRadius: 8,
                cursor: "pointer",
                transition: "all 0.2s"
              }}
            >
              <div className="selection-indicator" style={{
                width: 14, height: 14, borderRadius: "50%", border: "1px solid var(--border-color)",
                display: "flex", alignItems: "center", justifyContent: "center",
                background: n2yoStatus ? "var(--primary)" : "transparent"
              }}>
                {n2yoStatus && <Check size={8} color="#000" strokeWidth={3} />}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "#fff" }}>N2YO API Key</div>
                <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2 }}>
                  {n2yoStatus ? "ACTIVE - LIVE DATA ENABLED" : "DISABLED - API KEY REQUIRED"}
                </div>
              </div>
              <button
                className="btn"
                style={{ padding: "4px", opacity: 0.6 }}
                onClick={(e) => {
                  e.stopPropagation();
                  setEditingN2yo(!editingN2yo);
                  setN2yoKeyInput("");
                }}
              >
                <Edit2 size={12} />
              </button>
            </div>

            {editingN2yo && (
              <div className="glass-panel" style={{ padding: "10px", borderRadius: "10px", border: "1px solid var(--primary-dim)" }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <div style={{ flex: 1, position: "relative" }}>
                    <Key size={12} style={{ position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)", opacity: 0.5 }} />
                    <input
                      type="password"
                      placeholder="Enter N2YO API Key"
                      value={n2yoKeyInput}
                      onChange={(e) => setN2yoKeyInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && n2yoKeyInput.trim()) {
                          handleSaveN2yoKey();
                        }
                      }}
                      style={{
                        width: "100%",
                        background: "rgba(0,0,0,0.3)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "6px",
                        padding: "6px 8px 6px 28px",
                        fontSize: "12px",
                        color: "#fff",
                        outline: "none",
                      }}
                      autoFocus
                    />
                  </div>
                  <button
                    className="btn btn-primary"
                    style={{ padding: "6px" }}
                    disabled={isSaving || !n2yoKeyInput.trim()}
                    onClick={handleSaveN2yoKey}
                  >
                    <Save size={14} />
                  </button>
                   {n2yoStatus && (
                    confirmingDelete === "n2yo" ? (
                      <>
                        <button
                          className="btn btn-primary"
                          style={{ padding: "4px 8px", fontSize: "10px", background: "var(--critical)", border: "1px solid var(--critical)" }}
                          disabled={isSaving}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteN2yoKey();
                            setConfirmingDelete(null);
                          }}
                        >
                          Confirm
                        </button>
                        <button
                          className="btn"
                          style={{ padding: "4px 8px", fontSize: "10px" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmingDelete(null);
                          }}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        className="btn"
                        style={{ padding: "6px", color: "var(--critical)" }}
                        disabled={isSaving}
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmingDelete("n2yo");
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    )
                  )}
                </div>
                {saveStatus && saveStatus.type === "error" && (
                  <div style={{ fontSize: "10px", color: "var(--critical)", marginTop: 6 }}>{saveStatus.msg}</div>
                )}
              </div>
            )}
          </div>

          {/* Observer GPS Panel */}
          <div className="glass-panel" style={{ 
            padding: "16px 14px", 
            borderRadius: "10px", 
            border: "1px solid var(--border-color)",
            background: "rgba(0,0,0,0.2)",
            display: "flex",
            flexDirection: "column",
            gap: 12
          }}>
            <div style={{ fontSize: "12px", color: "#fff", fontWeight: 600 }}>
              Observer Location:
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", width: 70 }}>Latitude:</span>
                <input
                  type="text"
                  value={latInput}
                  onChange={(e) => setLatInput(e.target.value)}
                  onBlur={handleApplyObserver}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleApplyObserver();
                  }}
                  style={{
                    flex: 1,
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    fontSize: "12px",
                    color: "#fff",
                    outline: "none"
                  }}
                />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", width: 70 }}>Longitude:</span>
                <input
                  type="text"
                  value={lngInput}
                  onChange={(e) => setLngInput(e.target.value)}
                  onBlur={handleApplyObserver}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleApplyObserver();
                  }}
                  style={{
                    flex: 1,
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    fontSize: "12px",
                    color: "#fff",
                    outline: "none"
                  }}
                />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", width: 70 }}>Alt (m):</span>
                <input
                  type="text"
                  value={altInput}
                  onChange={(e) => setAltInput(e.target.value)}
                  onBlur={handleApplyObserver}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleApplyObserver();
                  }}
                  style={{
                    flex: 1,
                    background: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "4px 8px",
                    fontSize: "12px",
                    color: "#fff",
                    outline: "none"
                  }}
                />
              </div>
            </div>
            <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: 2, fontStyle: "italic" }}>
              Tracking angles computed relative to observer coordinates.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
