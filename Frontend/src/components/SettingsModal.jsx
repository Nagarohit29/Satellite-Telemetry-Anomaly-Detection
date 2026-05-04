import React, { useState, useEffect } from "react";
import { getLLMModels, updateAPIKey, deleteAPIKey } from "../api/endpoints";
import { X, Check, Edit2, Save, Trash2, Key, Loader2, RefreshCw, Monitor, Cloud } from "lucide-react";

const CLOUD_MODELS_WITH_KEYS = ["ollama_cloud", "gemini", "openai", "anthropic"];

const SettingsModal = ({ isOpen, onClose, selectedModel, setSelectedModel }) => {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingProvider, setEditingProvider] = useState(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [confirmingDelete, setConfirmingDelete] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchModels();
      setSaveStatus(null);
    }
  }, [isOpen]);

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
      await updateAPIKey(provider, key, false);
      setEditingProvider(null);
      setApiKeyInput("");
      setSaveStatus({ type: "success", msg: `${provider} key loaded for this session.` });
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

  const needsApiKey = (modelId) => CLOUD_MODELS_WITH_KEYS.includes(modelId);

  const getStatusText = (model) => {
    if (selectedModel === model.id && model.available && model.ready !== false) return "CURRENTLY ACTIVE";
    if (model.status_text) return model.status_text;
    if (model.available) return "AVAILABLE - CLICK TO SELECT";
    if (model.type === "device") return "SERVER NOT RUNNING";
    return "MISSING API KEY";
  };

  if (!isOpen) return null;

  const deviceModels = models.filter((m) => m.type === "device");
  const cloudModels = models.filter((m) => m.type === "cloud");

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />

      <div className="glass-panel settings-popover">
        <div className="settings-header">
          <div className="settings-title">AI Preferences</div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
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
            <button onClick={onClose} className="btn" style={{ padding: "4px", background: "transparent", border: "none" }}>
              <X size={16} />
            </button>
          </div>
        </div>

        {saveStatus && (
          <div
            style={{
              padding: "8px 12px",
              marginBottom: "12px",
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
            Model Selection
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
                alignItems: "center",
                gap: 8,
              }}
            >
              <span style={{ fontSize: "12px", fontWeight: 700 }}>AUTO</span>
              <span>
                <strong>Auto Fallback</strong> - If Local Ollama is online, the system uses it by default. Select a cloud model to override.
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
                <Loader2 className="animate-spin" size={10} color="var(--primary)" /> Loading models...
              </div>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="skeleton skeleton-card" style={{ animationDelay: `${i * 0.15}s` }} />
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
            <div className="model-list">
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
                    className={`model-card ${selectedModel === model.id ? "selected" : ""} ${!model.available ? "disabled" : ""}`}
                    onClick={() => {
                      if (!model.available) return;
                      if (selectedModel === model.id) {
                        setSelectedModel("");
                        localStorage.removeItem("selectedModel");
                      } else {
                        setSelectedModel(model.id);
                      }
                    }}
                  >
                    <div className="selection-indicator">{selectedModel === model.id && <Check size={10} color="#000" />}</div>
                    <div className="model-info">
                      <div className="model-name">{model.name}</div>
                      <div className="model-status">{getStatusText(model)}</div>
                    </div>
                  </div>
                </div>
              ))}

              {cloudModels.length > 0 && (
                <div
                  style={{
                    fontSize: "10px",
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    marginTop: "12px",
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
                  >
                    <div className="selection-indicator">{selectedModel === model.id && <Check size={10} color="#000" />}</div>
                    <div className="model-info">
                      <div className="model-name">{model.name}</div>
                      <div className="model-status">{getStatusText(model)}</div>
                    </div>
                    {needsApiKey(model.id) && (
                      <button
                        className="btn"
                        style={{ padding: "6px", opacity: 0.6 }}
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
                        <Edit2 size={14} />
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

        <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }} onClick={onClose}>
          Confirm Settings
        </button>
      </div>
    </>
  );
};

export default SettingsModal;
