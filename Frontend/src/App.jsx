import { useState, useEffect } from "react";
import { Activity, AlertTriangle, UploadCloud, Settings, Satellite, Server } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Upload from "./pages/Upload";
import StatusBar from "./components/StatusBar";
import AIAssistant from "./components/AIAssistant";
import SettingsModal from "./components/SettingsModal";

export default function App() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem("selectedModel") || "";
  });

  // Persist selected model (or clear it when deselected)
  useEffect(() => {
    if (selectedModel) {
      localStorage.setItem("selectedModel", selectedModel);
    } else {
      localStorage.removeItem("selectedModel");
    }
  }, [selectedModel]);

  const tabs = [
    { id: "Dashboard", icon: Activity, label: "Live Telemetry" },
    { id: "Alerts", icon: AlertTriangle, label: "Incident Alerts" },
    { id: "Upload", icon: UploadCloud, label: "Batch Inference" },
  ];

  const pages = {
    Dashboard: <Dashboard selectedModel={selectedModel} />,
    Alerts: <Alerts />,
    Upload: <Upload />
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Sidebar */}
      <div className="glass-panel" style={{ 
        width: "260px", 
        borderLeft: "none", 
        borderTop: "none", 
        borderBottom: "none",
        borderRadius: 0,
        display: "flex",
        flexDirection: "column",
        zIndex: 10
      }}>
        <div style={{ padding: "24px 20px", display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ 
            width: 32, height: 32, 
            borderRadius: 8, 
            background: "var(--primary-dim)",
            border: "1px solid var(--primary)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "var(--primary)"
          }}>
            <Satellite size={18} />
          </div>
          <div>
            <h1 style={{ fontSize: 16, margin: 0, color: "#fff" }}>STAD</h1>
            <div style={{ fontSize: 10, color: "var(--primary)", textTransform: "uppercase", letterSpacing: 1 }}>
              Anomaly Detection
            </div>
          </div>
        </div>

        <div style={{ padding: "10px", flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", padding: "10px 10px 4px", textTransform: "uppercase", letterSpacing: 1 }}>
            Main Menu
          </div>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "12px 14px",
                  background: isActive ? "var(--primary-dim)" : "transparent",
                  border: "1px solid",
                  borderColor: isActive ? "var(--border-glow)" : "transparent",
                  borderRadius: 8,
                  color: isActive ? "var(--primary)" : "var(--text-muted)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  textAlign: "left",
                  fontSize: 14,
                  fontWeight: isActive ? 600 : 500
                }}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </div>
        
        {/* Connection Status at bottom of sidebar */}
        <div style={{ padding: "20px", borderTop: "1px solid var(--border-color)" }}>
           <StatusBar />
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>
        
        {/* Header */}
        <header style={{ 
          height: "64px", 
          borderBottom: "1px solid var(--border-color)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 32px",
          background: "rgba(5, 5, 10, 0.4)",
          backdropFilter: "blur(10px)",
          zIndex: 5
        }}>
          <h2 style={{ fontSize: 18, margin: 0, fontWeight: 500 }}>
            {tabs.find(t => t.id === activeTab)?.label}
          </h2>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
             <div className="badge badge-success" style={{ display: "flex", alignItems: "center", gap: 6 }}>
               <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)" }} className="animate-pulse" />
               SYSTEM ONLINE
             </div>
             <div style={{ position: "relative" }}>
               <button className="btn" style={{ padding: 8 }} onClick={() => setIsSettingsOpen(true)}>
                 <Settings size={16} />
               </button>
               <SettingsModal 
                 isOpen={isSettingsOpen} 
                 onClose={() => setIsSettingsOpen(false)} 
                 selectedModel={selectedModel}
                 setSelectedModel={(model) => {
                   setSelectedModel(model);
                   localStorage.setItem("selectedModel", model);
                 }}
               />
             </div>
          </div>
        </header>

        {/* Scrollable Page Content */}
        <main style={{ flex: 1, overflowY: "auto", padding: "32px", position: "relative" }}>
          <div className="slide-in" key={activeTab}>
            {pages[activeTab]}
          </div>
        </main>
        
        {/* AI Assistant Chat Component */}
        <AIAssistant selectedModel={selectedModel} />
      </div>
    </div>
  );
}