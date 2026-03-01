import { useEffect, useMemo, useState } from "react";
import { useLocationData } from "../context/LocationContext";

const WEATHER_LABELS = {
  0: "Clear",
  1: "Mostly clear",
  2: "Partly cloudy",
  3: "Cloudy",
  45: "Fog",
  48: "Fog",
  51: "Light drizzle",
  53: "Drizzle",
  55: "Heavy drizzle",
  61: "Light rain",
  63: "Rain",
  65: "Heavy rain",
  80: "Rain showers",
  95: "Thunderstorm",
};

function formatIST(date) {
  return date.toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function WeatherTimeWidget() {
  const { coords, place } = useLocationData();
  const [now, setNow] = useState(new Date());
  const [weather, setWeather] = useState({ temperature: "--", weatherCode: null, wind: "--" });

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadWeather = async () => {
      try {
        const response = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${coords.latitude}&longitude=${coords.longitude}&current=temperature_2m,weather_code,wind_speed_10m&timezone=Asia%2FKolkata`
        );
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        if (!mounted) return;
        setWeather({
          temperature: data.current?.temperature_2m ?? "--",
          weatherCode: data.current?.weather_code ?? null,
          wind: data.current?.wind_speed_10m ?? "--",
        });
      } catch {
        // keep previous values
      }
    };

    loadWeather();
    const poll = setInterval(loadWeather, 300000);
    return () => {
      mounted = false;
      clearInterval(poll);
    };
  }, [coords.latitude, coords.longitude]);

  const weatherLabel = useMemo(() => WEATHER_LABELS[weather.weatherCode] || "Weather", [weather.weatherCode]);

  return (
    <div className="weather-time-widget" aria-label="India time and weather">
      <p className="wt-time">IST {formatIST(now)}</p>
      <p className="wt-weather">
        {weather.temperature}C | {weatherLabel}
      </p>
      <p className="wt-place">
        {place.locality || place.district || "Tamil Nadu"}, {place.state || "Tamil Nadu"}
      </p>
    </div>
  );
}

export default WeatherTimeWidget;
