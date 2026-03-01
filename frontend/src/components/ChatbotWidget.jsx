import { useState } from "react";

function ChatbotWidget({ onAsk }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Vanakkam. I am your farm assistant. Ask me about prediction, recommendations, surveys, or local farming guidance.",
    },
  ]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const history = messages.slice(-10).map((message) => ({
        role: message.role,
        content: message.content,
      }));
      const result = await onAsk({ message: text, history });
      const assistantText = result?.reply || "No response from assistant.";
      setMessages((prev) => [...prev, { role: "assistant", content: assistantText }]);
      if (result?.toolSummaries?.length) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Actions: ${result.toolSummaries.join(" | ")}`,
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card assistant-card">
      <div className="card-head">
        <h3>Gemini Assistant</h3>
        <p>Tamil and English support, with app actions</p>
      </div>
      <div className="chatbot-panel embedded">
        <div className="chatbot-messages">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
              {message.content}
            </div>
          ))}
        </div>
        <div className="chatbot-input">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask in Tamil or English..."
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleSend();
              }
            }}
          />
          <button type="button" onClick={handleSend} disabled={loading}>
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </section>
  );
}

export default ChatbotWidget;
