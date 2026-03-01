import { useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "../context/LanguageContext";

function resolveVoice(voices, targetLang) {
  if (!voices.length) return null;
  const exact = voices.find((voice) => voice.lang === targetLang);
  if (exact) return exact;
  const prefix = targetLang.split("-")[0];
  const partial = voices.find((voice) => voice.lang?.toLowerCase().startsWith(prefix.toLowerCase()));
  return partial || voices[0];
}

function ChatbotWidget({ onAsk }) {
  const { isTamil } = useLanguage();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const [voices, setVoices] = useState([]);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Vanakkam. I am your farm assistant. Ask me about prediction, recommendations, surveys, or local farming guidance.",
    },
  ]);

  const recognitionRef = useRef(null);
  const currentLang = isTamil ? "ta-IN" : "en-IN";

  const speechRecognitionCtor = useMemo(() => {
    if (typeof window === "undefined") return null;
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }, []);

  const speechSynthesisSupported = useMemo(
    () => typeof window !== "undefined" && "speechSynthesis" in window,
    []
  );

  useEffect(() => {
    if (!speechSynthesisSupported) return;

    const updateVoices = () => {
      setVoices(window.speechSynthesis.getVoices() || []);
    };

    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;

    return () => {
      window.speechSynthesis.onvoiceschanged = null;
      window.speechSynthesis.cancel();
    };
  }, [speechSynthesisSupported]);

  useEffect(() => {
    if (!speechRecognitionCtor) return;

    const recognition = new speechRecognitionCtor();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.lang = currentLang;

    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim() || "";
      if (!transcript) return;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      setVoiceError("");
    };

    recognition.onerror = () => {
      setListening(false);
      setVoiceError("Voice input could not be captured. Please try again.");
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.stop();
      } catch {
        // ignore cleanup stop errors
      }
      recognitionRef.current = null;
    };
  }, [speechRecognitionCtor, currentLang]);

  const speakText = (text) => {
    if (!speechSynthesisSupported || !text) return;
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = currentLang;
      const voice = resolveVoice(voices, currentLang);
      if (voice) {
        utterance.voice = voice;
      }
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      setVoiceError("");
    } catch {
      setVoiceError("Voice playback failed. Please check browser voice settings.");
    }
  };

  const toggleListening = () => {
    if (!speechRecognitionCtor || !recognitionRef.current) {
      setVoiceError("Voice input is not supported in this browser.");
      return;
    }
    try {
      if (listening) {
        recognitionRef.current.stop();
        setListening(false);
      } else {
        setVoiceError("");
        recognitionRef.current.lang = currentLang;
        recognitionRef.current.start();
        setListening(true);
      }
    } catch {
      setListening(false);
      setVoiceError("Microphone access failed. Allow microphone permission and try again.");
    }
  };

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

      if (autoSpeak) {
        speakText(assistantText);
      }

      if (result?.toolSummaries?.length) {
        const actionsText = `Actions: ${result.toolSummaries.join(" | ")}`;
        setMessages((prev) => [...prev, { role: "assistant", content: actionsText }]);
        if (autoSpeak) {
          speakText(actionsText);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card assistant-card">
      <div className="card-head">
        <h3>Gemini Assistant</h3>
        <p>Tamil and English support, with app actions and voice assistant</p>
      </div>

      <div className="voice-controls">
        <button
          type="button"
          className={listening ? "voice-btn active" : "voice-btn"}
          onClick={toggleListening}
          disabled={!speechRecognitionCtor}
        >
          {listening ? "Stop Mic" : "Start Mic"}
        </button>
        <button
          type="button"
          className={autoSpeak ? "voice-btn active" : "voice-btn"}
          onClick={() => setAutoSpeak((prev) => !prev)}
          disabled={!speechSynthesisSupported}
        >
          {autoSpeak ? "Auto Voice On" : "Auto Voice Off"}
        </button>
        <small className="muted">Voice mode: {currentLang}</small>
      </div>
      {voiceError ? <p className="error-line">{voiceError}</p> : null}

      <div className="chatbot-panel embedded">
        <div className="chatbot-messages">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
              <p>{message.content}</p>
              {message.role === "assistant" && speechSynthesisSupported ? (
                <button
                  type="button"
                  className="inline-voice-btn"
                  onClick={() => speakText(message.content)}
                >
                  Speak
                </button>
              ) : null}
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
