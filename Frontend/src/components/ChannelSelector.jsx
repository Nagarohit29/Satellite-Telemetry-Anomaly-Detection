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
      style={{ padding: "6px 12px", borderRadius: 6, fontSize: 13 }}
    >
      {channels.map((ch) => (
        <option key={ch} value={ch}>{ch}</option>
      ))}
    </select>
  );
}