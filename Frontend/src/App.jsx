import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Upload from "./pages/Upload";
import StatusBar from "./components/StatusBar";

const tabs = ["Dashboard", "Alerts", "Upload"];

export default function App() {
  const [activeTab, setActiveTab] = useState("Dashboard");

  const pages = { Dashboard: <Dashboard />, Alerts: <Alerts />, Upload: <Upload /> };

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d1a", fontFamily: "sans-serif" }}>
      <StatusBar />
      <div style={{
        display: "flex", alignItems: "center", gap: 0,
        padding: "0 20px", background: "#12122a",
        borderBottom: "1px solid #222"
      }}>
        <span style={{ fontSize: 15, fontWeight: 500, color: "#fff", marginRight: 24, padding: "14px 0" }}>
          SatelliteAD
        </span>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: "14px 16px", fontSize: 13, color: activeTab === tab ? "#378ADD" : "#888",
              borderBottom: activeTab === tab ? "2px solid #378ADD" : "2px solid transparent"
            }}
          >
            {tab}
          </button>
        ))}
      </div>
      <div>{pages[activeTab]}</div>
    </div>
  );
}