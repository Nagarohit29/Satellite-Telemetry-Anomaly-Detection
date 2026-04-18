import { useState, useRef, useEffect } from "react";
import { MessageSquare, X, Send, Cpu, User } from "lucide-react";
import { sendChatMessage } from "../api/endpoints";

export default function AIAssistant({ selectedModel }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "NASA STAD AI Assistant online. How can I help you analyze telemetry anomalies today?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    
    // Add to UI immediately
    const newMessages = [...messages, { role: "user", content: userMsg }];
    setMessages(newMessages);
    setLoading(true);

    try {
      // Send history to API
      // Filter out only role and content for API
      const apiMessages = newMessages.map(m => ({ role: m.role, content: m.content }));
      
      const contextStr = "User is currently viewing the dashboard."; // In a full implementation, you could pass the current channel/stats here.
      
      const response = await sendChatMessage(apiMessages, contextStr, selectedModel);
      
      setMessages([...newMessages, { role: "assistant", content: response.response }]);
    } catch (err) {
      setMessages([...newMessages, { 
        role: "assistant", 
        content: "ERROR: Communication link with AI Core severed. Please check system health.",
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="glass-panel"
        style={{
          position: "absolute",
          bottom: "32px",
          right: "32px",
          width: 56,
          height: 56,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          border: isOpen ? "1px solid var(--primary)" : "1px solid var(--border-color)",
          color: isOpen ? "var(--primary)" : "#fff",
          zIndex: 100,
          boxShadow: isOpen ? "0 0 20px var(--primary-dim)" : "0 4px 12px rgba(0,0,0,0.5)"
        }}
      >
        {isOpen ? <X size={24} /> : <MessageSquare size={24} />}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div 
          className="glass-panel slide-in"
          style={{
            position: "absolute",
            bottom: "100px",
            right: "32px",
            width: 380,
            height: 500,
            display: "flex",
            flexDirection: "column",
            zIndex: 99,
            boxShadow: "0 10px 40px rgba(0,0,0,0.8)"
          }}
        >
          {/* Header */}
          <div style={{
            padding: "16px",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            gap: 12,
            background: "rgba(0, 229, 255, 0.05)",
            borderTopLeftRadius: 12,
            borderTopRightRadius: 12
          }}>
            <Cpu size={20} color="var(--primary)" />
            <div>
              <h3 style={{ margin: 0, fontSize: 14, color: "#fff" }}>AI Analyst</h3>
              <div style={{ fontSize: 10, color: "var(--success)", display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)", display: "inline-block" }} className="animate-pulse" />
                Online
              </div>
            </div>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: 16
          }}>
            {messages.map((msg, idx) => (
              <div key={idx} style={{
                display: "flex",
                gap: 12,
                flexDirection: msg.role === "user" ? "row-reverse" : "row"
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                  background: msg.role === "user" ? "rgba(255,255,255,0.1)" : "var(--primary-dim)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: msg.role === "user" ? "#fff" : "var(--primary)"
                }}>
                  {msg.role === "user" ? <User size={14} /> : <Cpu size={14} />}
                </div>
                <div style={{
                  background: msg.role === "user" ? "var(--bg-panel-hover)" : "rgba(0, 229, 255, 0.05)",
                  border: msg.role === "user" ? "1px solid var(--border-color)" : "1px solid var(--primary-dim)",
                  padding: "10px 14px",
                  borderRadius: 12,
                  borderTopRightRadius: msg.role === "user" ? 0 : 12,
                  borderTopLeftRadius: msg.role === "assistant" ? 0 : 12,
                  fontSize: 13,
                  lineHeight: 1.5,
                  color: msg.isError ? "var(--critical)" : "var(--text-main)",
                  maxWidth: "80%"
                }}>
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                  background: "var(--primary-dim)", display: "flex", alignItems: "center", justifyContent: "center",
                  color: "var(--primary)"
                }}>
                  <Cpu size={14} />
                </div>
                <div style={{
                  background: "rgba(0, 229, 255, 0.05)", border: "1px solid var(--primary-dim)",
                  padding: "10px 14px", borderRadius: 12, borderTopLeftRadius: 0,
                  fontSize: 13, color: "var(--primary)"
                }} className="animate-pulse">
                  Processing...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div style={{
            padding: "16px",
            borderTop: "1px solid var(--border-color)",
            display: "flex",
            gap: 8
          }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about anomalies..."
              style={{
                flex: 1,
                background: "rgba(0,0,0,0.3)",
                border: "1px solid var(--border-color)",
                borderRadius: 8,
                padding: "10px 14px",
                color: "#fff",
                fontSize: 13,
                outline: "none",
                fontFamily: "var(--font-inter)"
              }}
            />
            <button 
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="btn btn-primary"
              style={{ padding: "0 14px" }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
