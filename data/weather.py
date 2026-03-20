"""
data/weather.py — QCEX Weather & Macro Indicators
Fetches or synthesises weather/macro data relevant to commodity pricing.

Real sources used when available:
  - Open-Meteo (free, no API key): temperature, precipitation
  - Synthetic ENSO / HDD / storage indices as fallback

Economic significance:
  Cacao  : ENSO (El Niño) → West Africa rainfall → crop yield
  Gas TTF: HDD (Heating Degree Days) → heating demand → price spikes
  Uranium: No direct weather link — uses reactor count as proxy
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ── Key locations per commodity ───────────────────────────────────────────────
LOCATIONS = {
    "cocoa":   {"lat": 5.35,   "lon": -4.00,  "city": "Abidjan, Ivory Coast"},
    "gas":     {"lat": 52.52,  "lon": 13.40,  "city": "Berlin, Germany"},
    "uranium": {"lat": 51.18,  "lon": 71.45,  "city": "Astana, Kazakhstan"},
}

def fetch_weather(commodity: str, days: int = 90) -> pd.DataFrame:
    """
    Fetch recent temperature and precipitation for commodity's key location.
    Uses Open-Meteo free API (no key needed). Falls back to synthetic if offline.
    """
    loc = LOCATIONS.get(commodity, LOCATIONS["gas"])
    try:
        import urllib.request, json
        end   = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={loc['lat']}&longitude={loc['lon']}"
            f"&start_date={start}&end_date={end}"
            f"&daily=temperature_2m_mean,precipitation_sum"
            f"&timezone=UTC"
        )
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        df = pd.DataFrame({
            "date":   pd.to_datetime(data["daily"]["time"]),
            "temp_c": data["daily"]["temperature_2m_mean"],
            "precip": data["daily"]["precipitation_sum"],
        }).set_index("date").dropna()
        df.attrs["source"] = "open-meteo"
        df.attrs["location"] = loc["city"]
        return df
    except Exception:
        return _synthetic_weather(commodity, days, loc["city"])


def _synthetic_weather(commodity: str, days: int, city: str) -> pd.DataFrame:
    """Synthetic weather using seasonal patterns calibrated to location."""
    rng   = np.random.default_rng(42)
    dates = pd.date_range(end=datetime.today(), periods=days, freq="D")
    doy   = np.array([d.timetuple().tm_yday for d in dates])

    if commodity == "cocoa":
        # Tropical: warm (~28°C), dry season Jan-Mar, wet Apr-Jul
        temp   = 28 + 3 * np.sin(2*np.pi*(doy-80)/365) + rng.normal(0, 1, days)
        precip = np.clip(5 + 4 * np.sin(2*np.pi*(doy-120)/365) + rng.exponential(2, days), 0, None)
    elif commodity == "gas":
        # Germany: cold winters (~2°C), warm summers (~22°C)
        temp   = 12 + 10 * np.sin(2*np.pi*(doy-200)/365) + rng.normal(0, 2, days)
        precip = rng.exponential(2.5, days)
    else:
        # Kazakhstan: continental — very cold winters, hot summers
        temp   = 12 + 18 * np.sin(2*np.pi*(doy-200)/365) + rng.normal(0, 3, days)
        precip = rng.exponential(1.0, days)

    df = pd.DataFrame({"temp_c": temp, "precip": precip}, index=dates)
    df.attrs["source"]   = "synthetic"
    df.attrs["location"] = city
    return df


def compute_weather_indicators(commodity: str, df_weather: pd.DataFrame) -> dict:
    """
    Compute commodity-specific weather indicators from raw weather data.

    Returns dict of indicators with value, trend, and pricing impact.
    """
    temp   = df_weather["temp_c"].dropna()
    precip = df_weather["precip"].dropna()

    if commodity == "cocoa":
        # ENSO proxy: deviation of precipitation from seasonal norm
        precip_30d   = precip.tail(30).mean()
        precip_norm  = precip.mean()
        enso_proxy   = (precip_30d - precip_norm) / (precip_norm + 0.1)
        drought_days = int((precip.tail(30) < 0.5).sum())
        temp_anom    = float(temp.tail(30).mean() - temp.mean())

        impact = "BEARISH" if enso_proxy > 0.2 else ("BULLISH" if enso_proxy < -0.2 else "NEUTRAL")

        return {
            "location": df_weather.attrs.get("location", ""),
            "source":   df_weather.attrs.get("source", ""),
            "indicators": [
                {"name": "Precipitation 30d",   "value": f"{precip_30d:.1f} mm/día",
                 "trend": "up" if enso_proxy > 0 else "down",
                 "impact": "Normal harvest" if enso_proxy > 0 else "⚠ Risk sequía",
                 "color": "#4AFF99" if enso_proxy > 0 else "#FF4455"},
                {"name": "Dry days (30d)",    "value": f"{drought_days} días",
                 "trend": "up" if drought_days > 10 else "down",
                 "impact": f"{'⚠ Water stress' if drought_days > 15 else 'Normal'}",
                 "color": "#FF4455" if drought_days > 15 else "#4AFF99"},
                {"name": "Temperature anomaly",    "value": f"{temp_anom:+.1f}°C",
                 "trend": "up" if temp_anom > 0 else "down",
                 "impact": "Heat → lower yield" if temp_anom > 1 else "Normal",
                 "color": "#FF9944" if temp_anom > 1 else "#4AFF99"},
                {"name": "ENSO proxy",          "value": f"{enso_proxy:+.2f}",
                 "trend": "up" if enso_proxy > 0 else "down",
                 "impact": impact,
                 "color": "#4AFF99" if impact == "BEARISH" else ("#FF4455" if impact == "BULLISH" else "#F5D060")},
            ],
            "summary": f"Condiciones {'favorables para cosecha' if enso_proxy > 0.1 else 'de riesgo para oferta'} en {df_weather.attrs.get('location','')}",
            "price_impact": impact,
        }

    elif commodity == "gas":
        # HDD: Heating Degree Days (base 15.5°C)
        base    = 15.5
        hdd_30d = float(np.maximum(base - temp.tail(30), 0).sum())
        hdd_avg = float(np.maximum(base - temp, 0).mean() * 30)
        hdd_anom = (hdd_30d - hdd_avg) / (hdd_avg + 1) * 100
        temp_7d = float(temp.tail(7).mean())
        cold_days = int((temp.tail(30) < 0).sum())

        impact = "BULLISH" if hdd_anom > 15 else ("BEARISH" if hdd_anom < -15 else "NEUTRAL")

        return {
            "location": df_weather.attrs.get("location", ""),
            "source":   df_weather.attrs.get("source", ""),
            "indicators": [
                {"name": "HDD 30 days",        "value": f"{hdd_30d:.0f}",
                 "trend": "up" if hdd_anom > 0 else "down",
                 "impact": "↑ Heating demand" if hdd_anom > 10 else "Normal demand",
                 "color": "#FF7EB3" if hdd_anom > 15 else "#4AFF99"},
                {"name": "HDD anomaly",       "value": f"{hdd_anom:+.1f}%",
                 "trend": "up" if hdd_anom > 0 else "down",
                 "impact": f"vs historical average",
                 "color": "#FF7EB3" if hdd_anom > 0 else "#4AFF99"},
                {"name": "Avg temp 7d",     "value": f"{temp_7d:.1f}°C",
                 "trend": "down" if temp_7d < 5 else "up",
                 "impact": "⚠ Extreme cold" if temp_7d < 0 else "Normal",
                 "color": "#FF4455" if temp_7d < 0 else "#5BAEFF"},
                {"name": "Days below 0°C (30d)","value": f"{cold_days}",
                 "trend": "up" if cold_days > 10 else "down",
                 "impact": "Severe winter" if cold_days > 15 else "Normal",
                 "color": "#FF7EB3" if cold_days > 15 else "#4AFF99"},
            ],
            "summary": f"Invierno {'frío — upward pressure on TTF' if hdd_anom > 15 else 'suave — downward pressure on TTF' if hdd_anom < -15 else 'normal — no extra pressure'}",
            "price_impact": impact,
        }

    else:  # uranium
        temp_mean = float(temp.tail(30).mean())
        return {
            "location": df_weather.attrs.get("location", ""),
            "source":   df_weather.attrs.get("source", ""),
            "indicators": [
                {"name": "Kazakhstan temp",   "value": f"{temp_mean:.1f}°C",
                 "trend": "neutral", "impact": "No direct price impact",
                 "color": "#4AFF99"},
                {"name": "Main driver",   "value": "Política nuclear",
                 "trend": "up", "impact": "62 reactors under construction",
                 "color": "#4AFF99"},
                {"name": "Kazatomprom supply", "value": "−12% 2024",
                 "trend": "down", "impact": "↑ Upward pressure",
                 "color": "#FF4455"},
                {"name": "L-T demand",        "value": "+8% CAGR",
                 "trend": "up", "impact": "Global nuclear expansion",
                 "color": "#4AFF99"},
            ],
            "summary": "Uranium: price driven by energy policy, not weather.",
            "price_impact": "BULLISH",
        }
