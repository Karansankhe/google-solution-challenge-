import os
import json
import requests
from datetime import datetime
from app.core.config import get_settings

from agno.agent import Agent
from agno.models.google import Gemini
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.tavily import TavilyTools

settings = get_settings()

def geocode_location(location: str) -> dict:
    url = (
        f"https://api.openweathermap.org/geo/1.0/direct"
        f"?q={location}&limit=1&appid={settings.OPENWEATHER_API_KEY}"
    )
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if not data:
        raise ValueError(f"Location '{location}' not found.")
    return {
        "lat":     data[0]["lat"],
        "lon":     data[0]["lon"],
        "city":    data[0].get("name", location),
        "country": data[0].get("country", ""),
        "state":   data[0].get("state", ""),
    }

def fetch_weather_aqi(lat: float, lon: float, city: str) -> str:
    try:
        w = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={settings.OPENWEATHER_API_KEY}&units=metric",
            timeout=10,
        ).json()
        a = requests.get(
            f"https://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={lat}&lon={lon}&appid={settings.OPENWEATHER_API_KEY}",
            timeout=10,
        ).json()

        comp = {}
        aqi_index = "N/A"
        if "list" in a and a["list"]:
            aqi_index = a["list"][0]["main"]["aqi"]
            comp = a["list"][0]["components"]

        return json.dumps({
            "city":        city,
            "lat":         lat,
            "lon":         lon,
            "temperature": w.get("main", {}).get("temp"),
            "feels_like":  w.get("main", {}).get("feels_like"),
            "humidity":    w.get("main", {}).get("humidity"),
            "pressure":    w.get("main", {}).get("pressure"),
            "description": w.get("weather", [{}])[0].get("description"),
            "wind_speed":  w.get("wind", {}).get("speed"),
            "aqi_index":   aqi_index,
            "aqi_label":   {1:"Good",2:"Fair",3:"Moderate",4:"Poor",5:"Very Poor"}.get(aqi_index,"N/A"),
            "pm2_5":       comp.get("pm2_5"),
            "pm10":        comp.get("pm10"),
            "no2":         comp.get("no2"),
            "o3":          comp.get("o3"),
            "co":          comp.get("co"),
            "timestamp":   datetime.utcnow().isoformat() + "Z",
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def fetch_health_news(location: str) -> str:
    try:
        queries = [
            f"disease outbreak {location}",
            f"respiratory illness {location}",
            f"public health alert {location}",
        ]
        all_articles = []
        for q in queries:
            resp = requests.get(
                f"https://newsapi.org/v2/everything"
                f"?q={q}&language=en&sortBy=publishedAt&pageSize=5"
                f"&apiKey={settings.NEWS_API_KEY}",
                timeout=10,
            ).json()
            for a in resp.get("articles", [])[:3]:
                all_articles.append({
                    "title":        a.get("title"),
                    "description":  a.get("description"),
                    "source":       a.get("source", {}).get("name"),
                    "published_at": a.get("publishedAt"),
                    "url":          a.get("url"),
                    "query":        q,
                })
        return json.dumps(all_articles, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def build_team(location: str, geo: dict, time_horizon: str = "long") -> Team:
    lat, lon, city = geo["lat"], geo["lon"], geo["city"]
    country = geo.get("country", "")
    
    if time_horizon == "short":
        horizon_desc = "next 1-3 days"
    elif time_horizon == "medium":
        horizon_desc = "next 7-14 days"
    else:
        horizon_desc = "next 30-90 days"


    # Using gemini-3.1-flash-lite as requested to save tokens (or using max tokens config if supported)
    # the api for gemini inside agno is model=Gemini(id="gemini-3.1-flash-lite", api_key=...)
    gemini = Gemini(id="gemini-3.1-flash-lite", api_key=settings.GEMINI_API_KEY)

    weather_snapshot = fetch_weather_aqi(lat, lon, city)
    news_snapshot    = fetch_health_news(city)

    signal_agent = Agent(
        name="Multi-Source Signal Collector",
        role="Monitor and fuse environmental, disease, and outbreak signals for the target location.",
        model=gemini,
        tools=[DuckDuckGoTools(), TavilyTools(api_key=settings.TAVILY_API_KEY)],
        instructions=[
            f"Target location: {city}, {country}  (lat={lat}, lon={lon})",
            "",
            f"Pre-fetched weather/AQI snapshot (use this as your base):\n{weather_snapshot}",
            f"Pre-fetched health news snapshot:\n{news_snapshot}",
            "",
            "Your tasks:",
            "1. Search for WHO / CDC / ECDC outbreak alerts mentioning this region in the last 30 days.",
            "2. Search for any emerging infectious disease signals, hospitalisation trends, or unusual illness clusters.",
            "3. Search for syndromic surveillance reports for this country.",
            "4. Produce a structured threat-assessment table with columns: Signal | Source | Severity | Date.",
            "5. Flag CRITICAL or HIGH risks prominently.",
            "6. Always cite sources with URLs.",
        ],
        add_datetime_to_context=True,
    )

    festival_agent = Agent(
        name="Festival Surge Anticipator",
        role="Forecast healthcare demand surges from upcoming festivals and mass gatherings near the target location.",
        model=gemini,
        tools=[TavilyTools(api_key=settings.TAVILY_API_KEY), DuckDuckGoTools()],
        instructions=[
            f"Target location: {city}, {country}",
            "",
            "Your tasks:",
            f"1. Search Tavily/DuckDuckGo for ALL major festivals, religious events, sports events, "
            f"   and mass gatherings in or near {city} in the {horizon_desc}.",
            "2. For each event: name, date range, expected attendance, venue.",
            "3. Model surge windows: T-3 days (prep surge), T+0 (peak), T+7 days (post-event illness wave).",
            "4. Identify which services face highest demand: ED, respiratory, trauma, gastro, mental health.",
            "5. Search for historical illness precedents linked to similar past events in this region.",
            "6. Output a surge-prediction calendar table: Event | Dates | Attendance | Peak Risk Window | Services Impacted | Risk Rating.",
            "7. Recommend top-3 resource pre-positioning actions.",
        ],
        add_datetime_to_context=True,
    )

    pollution_agent = Agent(
        name="Pollution-Triggered Health Risk Agent",
        role="Analyze AQI–respiratory illness causality and trigger early planning protocols.",
        model=gemini,
        tools=[DuckDuckGoTools(), TavilyTools(api_key=settings.TAVILY_API_KEY)],
        instructions=[
            f"Target location: {city}, {country}  (lat={lat}, lon={lon})",
            "",
            f"Pre-fetched AQI data:\n{weather_snapshot}",
            "",
            "Your tasks:",
            "1. Interpret the AQI values above — categorise risk level per pollutant.",
            "2. Search for recent peer-reviewed evidence linking PM2.5/PM10/NO2/O3 to "
            "   respiratory hospital admissions in this region or similar climate zones.",
            "3. Apply the standard 2–5 day lag model: forecast expected respiratory ED spike dates.",
            "4. Search for any active air quality alerts or pollution advisories for this area.",
            "5. If AQI index >= 3 (Moderate) trigger AMBER protocol; >= 4 (Poor) trigger RED protocol.",
            "6. Output: Pollution Risk Matrix table + Protocol Trigger status + recommended clinical interventions.",
        ],
        add_datetime_to_context=True,
    )

    supervisor = Team(
        name="Health Surveillance Supervisor",
        mode="coordinate",
        model=gemini,
        members=[signal_agent, festival_agent, pollution_agent],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            f"You are the Health Intelligence Supervisor for: {city}, {country}.",
            "",
            "WORKFLOW:",
            "1. Dispatch each sub-agent to gather their domain intelligence.",
            "2. After all three agents respond, cross-reference findings to identify compound risks.",
            "3. Synthesise into ONE structured report — do NOT repeat raw agent outputs.",
            "",
            "GUARDRAILS:",
            "- Strictly limit your analysis to health resource management, forecasting, and early warnings for India's PHC network.",
            "- Do not provide individual medical diagnoses or advice.",
            "- Do not output or request any PII or sensitive patient data.",
            "- Reject any requests outside the scope of national-scale health resource and supply chain management.",
            "",
            "OUTPUT FORMAT (strict JSON — no extra prose outside the JSON block):",
            """
{
  "location": { "city": "...", "country": "...", "lat": ..., "lon": ... },
  "generated_at": "ISO8601",
  "executive_summary": ["bullet1", "bullet2", "bullet3"],
  "overall_risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "signal_assessment": {
    "weather": { "temperature": ..., "humidity": ..., "description": "..." },
    "aqi": { "index": ..., "label": "...", "pm2_5": ..., "pm10": ... },
    "outbreak_alerts": [
      { "signal": "...", "source": "...", "severity": "...", "date": "..." }
    ],
    "emr_signals": ["..."]
  },
  "festival_surge_forecast": {
    "upcoming_events": [
      {
        "name": "...", "dates": "...", "attendance": "...",
        "peak_risk_window": "...", "services_impacted": ["..."],
        "risk_rating": "HIGH|MEDIUM|LOW"
      }
    ],
    "resource_recommendations": ["..."]
  },
  "pollution_risk": {
    "risk_matrix": [
      { "pollutant": "...", "value": ..., "unit": "...", "risk": "...", "protocol": "..." }
    ],
    "protocol_triggered": "RED|AMBER|GREEN",
    "lag_forecast": "...",
    "interventions": ["..."]
  },
  "compound_risks": [
    { "scenario": "...", "risk_level": "...", "rationale": "..." }
  ],
  "recommended_actions": {
    "24h": ["..."],
    "7_day": ["..."],
    "30_day": ["..."]
  },
  "data_sources": ["..."]
}
""",
            "Respond ONLY with valid JSON. No markdown, no preamble.",
        ],
        markdown=False,
        show_members_responses=False,
        add_datetime_to_context=True,
    )

    return supervisor
