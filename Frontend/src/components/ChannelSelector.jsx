import { useState, useEffect } from "react";
import { getChannels } from "../api/endpoints";

export default function ChannelSelector({ value, onChange }) {
  const [channels, setChannels] = useState([]);

  useEffect(() => {
    getChannels()
      .then((data) => setChannels(data.channels || []))
      .catch(() => setChannels(Array.from({ length: 55 }, (_, i) => `T-${i + 1}`)));
  }, []);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ 
        padding: "8px 16px", 
        borderRadius: 8, 
        fontSize: 13,
        background: "rgba(5, 5, 10, 0.8)",
        border: "1px solid var(--border-color)",
        color: "var(--text-main)",
        outline: "none",
        fontFamily: "var(--font-inter)",
        cursor: "pointer",
        backdropFilter: "blur(10px)"
      }}
    >
      {channels.map((ch) => (
        <option key={ch} value={ch} style={{ background: "var(--bg-dark)" }}>{ch}</option>
      ))}
    </select>
  );
}