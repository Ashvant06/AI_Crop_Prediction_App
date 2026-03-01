import ChatbotWidget from "../components/ChatbotWidget";
import { chatApi } from "../api/client";
import { useLocationData } from "../context/LocationContext";
import { useLanguage } from "../context/LanguageContext";

function AssistantPage() {
  const { t } = useLanguage();
  const { coords, place } = useLocationData();

  const handleAskAssistant = async ({ message, history }) => {
    try {
      const response = await chatApi.sendMessage({
        message,
        history,
        context: {
          user_region: {
            latitude: coords.latitude,
            longitude: coords.longitude,
            locality: place.locality || place.district || "",
            state: place.state || "Tamil Nadu",
          },
          prediction_defaults: {
            state: place.state || "Tamil Nadu",
            district: place.district || "",
          },
        },
      });
      return {
        reply: response.data.reply,
        usedTools: response.data.used_tools || [],
        toolSummaries: response.data.tool_summaries || [],
      };
    } catch (error) {
      return {
        reply: error?.response?.data?.detail || "Assistant is temporarily unavailable.",
        usedTools: [],
        toolSummaries: [],
      };
    }
  };

  return (
    <div className="page-stack">
      <section className="card">
        <div className="card-head">
          <h3>{t("assistantTitle")}</h3>
          <p>Uses Gemini for natural chat and app command actions</p>
        </div>
      </section>
      <ChatbotWidget onAsk={handleAskAssistant} />
    </div>
  );
}

export default AssistantPage;
