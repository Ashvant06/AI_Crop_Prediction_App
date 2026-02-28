import { useState } from "react";

function ChatbotWidget({ onAsk }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello. I can guide you and run app actions. Ask naturally: predict yield, recommend crops, show summary, activities, or save survey."
    }
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
        content: message.content
      }));
      const result = await onAsk({ message: text, history });
      const assistantText = result?.reply || "No response from assistant.";
      setMessages((prev) => [...prev, { role: "assistant", content: assistantText }]);
      if (result?.toolSummaries?.length) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Actions: ${result.toolSummaries.join(" | ")}`
          }
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={open ? "chatbot chatbot-open" : "chatbot"}>
      <button type="button" className="chatbot-toggle" onClick={() => setOpen((prev) => !prev)}>
        {open ? "Close Assistant" : "AI Agro Assistant"}
      </button>
      {open ? (
        <div className="chatbot-panel">
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
              placeholder="Ask about irrigation, pests, yield..."
            />
            <button type="button" onClick={handleSend} disabled={loading}>
              {loading ? "..." : "Send"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default ChatbotWidget;
