import { createContext, useContext, useEffect, useMemo, useState } from "react";

const LANG_KEY = "crop_ai_lang";

const TRANSLATIONS = {
  en: {
    appTitle: "AI Crop Yield Prediction",
    appSubtitle: "Tamil Nadu Farmer Support Platform",
    navOverview: "Overview",
    navPrediction: "Prediction",
    navSurvey: "Survey",
    navDashboard: "Dashboard",
    navAssistant: "Assistant",
    signOut: "Sign out",
    switchToTamil: "Tamil",
    switchToEnglish: "English",
    requestLocation: "Use My Location",
    locationPending: "Detecting location...",
    locationReady: "Location ready",
    locationError: "Location unavailable",
    loginHeading: "AI Crop Yield Prediction System",
    loginDesc: "A simple and local-first app for Tamil Nadu farmers.",
    demoMode: "Continue in Demo Mode",
    authenticating: "Authenticating...",
    overviewTitle: "Welcome to AgroAI Tamil Nadu",
    overviewDesc:
      "Get district-aware predictions, simple surveys, weather-aware insights, and local crop advisories in easy language.",
    latestNews: "Latest Agriculture News",
    predictionTitle: "Yield Prediction",
    recommendationTitle: "Top Crop Recommendations",
    surveyTitle: "Farmer Survey",
    dashboardTitle: "Farm Activity Dashboard",
    assistantTitle: "Gemini Farm Assistant",
    summaryPredictions: "Predictions",
    summaryRecommendations: "Recommendations",
    summarySurveys: "Surveys",
    summaryLatestYield: "Latest Yield (q/acre)",
    noData: "No data available yet.",
  },
  ta: {
    appTitle: "AI பயிர் விளைச்சல் கணிப்பு",
    appSubtitle: "தமிழ்நாடு விவசாய உதவி தளம்",
    navOverview: "முகப்பு",
    navPrediction: "கணிப்பு",
    navSurvey: "கணக்கெடுப்பு",
    navDashboard: "புள்ளிவிவரம்",
    navAssistant: "உதவியாளர்",
    signOut: "வெளியேறு",
    switchToTamil: "தமிழ்",
    switchToEnglish: "English",
    requestLocation: "என் இடத்தை பயன்படுத்து",
    locationPending: "இடம் கண்டறிகிறது...",
    locationReady: "இடம் தயார்",
    locationError: "இடம் கிடைக்கவில்லை",
    loginHeading: "AI பயிர் விளைச்சல் கணிப்பு அமைப்பு",
    loginDesc: "தமிழ்நாடு விவசாயிகளுக்கான எளிய பயன்பாடு.",
    demoMode: "டெமோ முறையில் தொடரவும்",
    authenticating: "உள்நுழைகிறது...",
    overviewTitle: "AgroAI தமிழ்நாடு பயன்பாட்டிற்கு வரவேற்கிறோம்",
    overviewDesc:
      "மாவட்ட அடிப்படையிலான கணிப்புகள், எளிய கணக்கெடுப்பு, வானிலை தகவல் மற்றும் உள்ளூர் பயிர் ஆலோசனைகள்.",
    latestNews: "சமீபத்திய வேளாண் செய்திகள்",
    predictionTitle: "விளைச்சல் கணிப்பு",
    recommendationTitle: "சிறந்த பயிர் பரிந்துரைகள்",
    surveyTitle: "விவசாயி கணக்கெடுப்பு",
    dashboardTitle: "செயல்பாட்டு புள்ளிவிவரம்",
    assistantTitle: "Gemini விவசாய உதவியாளர்",
    summaryPredictions: "கணிப்புகள்",
    summaryRecommendations: "பரிந்துரைகள்",
    summarySurveys: "கணக்கெடுப்புகள்",
    summaryLatestYield: "சமீபத்திய விளைச்சல் (q/acre)",
    noData: "இன்னும் தரவு இல்லை.",
  },
};

const LanguageContext = createContext(null);

function getInitialLanguage() {
  const saved = localStorage.getItem(LANG_KEY);
  return saved === "ta" ? "ta" : "en";
}

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(getInitialLanguage);

  useEffect(() => {
    document.documentElement.lang = language === "ta" ? "ta" : "en";
  }, [language]);

  const toggleLanguage = () => {
    const next = language === "en" ? "ta" : "en";
    localStorage.setItem(LANG_KEY, next);
    setLanguage(next);
  };

  const t = (key) => TRANSLATIONS[language]?.[key] || TRANSLATIONS.en[key] || key;

  const value = useMemo(
    () => ({ language, isTamil: language === "ta", toggleLanguage, t }),
    [language]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return context;
}
