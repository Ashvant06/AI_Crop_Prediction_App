import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { newsApi } from "../api/client";
import { useLanguage } from "../context/LanguageContext";
import { useLocationData } from "../context/LocationContext";

function stripHtml(value = "") {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function OverviewPage() {
  const { t } = useLanguage();
  const { place, isTamilNadu } = useLocationData();
  const [newsItems, setNewsItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const loadNews = async () => {
      try {
        const response = await newsApi.getOverview(9);
        if (!mounted) return;
        setNewsItems(response.data?.items || []);
      } catch {
        if (!mounted) return;
        setNewsItems([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    loadNews();
    return () => {
      mounted = false;
    };
  }, []);

  const locationLabel = useMemo(() => {
    const locality = place.locality || place.district || "";
    const state = place.state || "Tamil Nadu";
    return locality ? `${locality}, ${state}` : state;
  }, [place]);

  return (
    <div className="page-stack">
      <section className="card hero-card">
        <p className="eyebrow">Tamil Nadu Focus</p>
        <h2>{t("overviewTitle")}</h2>
        <p>{t("overviewDesc")}</p>
        <p className="muted">Detected Region: {locationLabel}</p>
        <p className={isTamilNadu ? "status-line" : "warning-box"}>
          {isTamilNadu
            ? "Regional mode active for Tamil Nadu advisories."
            : "Location appears outside Tamil Nadu. App will still prioritize Tamil Nadu recommendations."}
        </p>
        <div className="hero-actions">
          <Link className="primary-btn" to="/prediction">
            {t("navPrediction")}
          </Link>
          <Link className="secondary-btn" to="/survey">
            {t("navSurvey")}
          </Link>
          <Link className="secondary-btn" to="/assistant">
            {t("navAssistant")}
          </Link>
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>{t("latestNews")}</h3>
          <p>Live feed in gallery mode for farmers and field workers</p>
        </div>
        {loading ? <p className="muted">Loading news...</p> : null}
        <div className="news-grid">
          {newsItems.map((item, index) => (
            <article key={`${item.url}-${index}`} className="news-card">
              <div className="news-image">
                {item.image_url ? <img src={item.image_url} alt={item.title} loading="lazy" /> : <span>Agri News</span>}
              </div>
              <div className="news-body">
                <h4>{item.title}</h4>
                <p>{stripHtml(item.summary || "")}</p>
                <small>{item.source || "News"}</small>
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noreferrer" className="news-link">
                    Open story
                  </a>
                ) : null}
              </div>
            </article>
          ))}
          {!loading && newsItems.length === 0 ? <p className="muted">{t("noData")}</p> : null}
        </div>
      </section>
    </div>
  );
}

export default OverviewPage;
