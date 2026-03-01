import { createContext, useContext, useEffect, useMemo, useState } from "react";

const DEFAULT_COORDS = { latitude: 13.0827, longitude: 80.2707 }; // Chennai

const LocationContext = createContext(null);

async function reverseLookup(latitude, longitude) {
  try {
    const response = await fetch(
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
    );
    if (!response.ok) {
      throw new Error("Reverse geocoding failed");
    }
    const data = await response.json();
    return {
      locality: data.city || data.locality || data.principalSubdivision || "",
      district: data.locality || data.city || data.principalSubdivision || "",
      state: data.principalSubdivision || "Tamil Nadu",
      country: data.countryName || "India",
    };
  } catch {
    return {
      locality: "",
      district: "",
      state: "Tamil Nadu",
      country: "India",
    };
  }
}

export function LocationProvider({ children }) {
  const [coords, setCoords] = useState(DEFAULT_COORDS);
  const [place, setPlace] = useState({ locality: "", district: "", state: "Tamil Nadu", country: "India" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const requestLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      return;
    }
    setLoading(true);
    setError("");

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        setCoords({ latitude, longitude });
        const region = await reverseLookup(latitude, longitude);
        setPlace(region);
        setLoading(false);
      },
      () => {
        setError("Location permission denied");
        setLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 120000,
      }
    );
  };

  useEffect(() => {
    requestLocation();
  }, []);

  const value = useMemo(
    () => ({
      coords,
      place,
      loading,
      error,
      requestLocation,
      isTamilNadu: String(place.state || "").toLowerCase().includes("tamil"),
    }),
    [coords, place, loading, error]
  );

  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useLocationData() {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error("useLocationData must be used inside LocationProvider");
  }
  return context;
}
