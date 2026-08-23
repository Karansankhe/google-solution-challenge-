import json
import os
import tempfile
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.surveillance import SurveillanceRequest, GeoResponse
from app.services.surveillance import geocode_location, build_team, fetch_weather_aqi, fetch_health_news
from app.services.memory import save_surveillance_report, retrieve_historical_context

router = APIRouter(tags=["Surveillance"])

@router.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}

@router.get("/geocode", response_model=GeoResponse)
def geocode(location: str):
    """Resolve a location string to coordinates."""
    try:
        geo = geocode_location(location)
        return geo
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/analyze")
async def analyze(req: SurveillanceRequest):
    """
    Run the full 3-agent health surveillance cycle for a given location.
    Returns a structured JSON intelligence report.
    """
    try:
        geo = geocode_location(req.location)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    team = build_team(req.location, geo, req.time_horizon.value)
    loop = asyncio.get_event_loop()

    def run_team():
        response = team.run(
            f"""
            Execute the full health intelligence cycle for: {geo['city']}, {geo['country']}
            Coordinates: lat={geo['lat']}, lon={geo['lon']}
            Today: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            Time Horizon for Planning: {req.time_horizon.value}

            Each agent must gather their domain signals, then the supervisor
            synthesises everything into the structured JSON report.
            """,
            stream=False,
        )
        return response.content if hasattr(response, "content") else str(response)

    raw = await loop.run_in_executor(None, run_team)

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        report = json.loads(clean)
        # Proactively save the intelligence report for the distribution endpoint
        with open(os.path.join(tempfile.gettempdir(), "latest_surveillance.json"), "w") as f:
            json.dump(report, f, indent=2)
    except Exception:
        report = {"raw_output": raw, "parse_error": "Agent did not return valid JSON"}

    return {
        "location": geo,
        "report":   report,
        "meta": {
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "agents_used":  ["Signal Collector", "Festival Surge Anticipator", "Pollution Risk Agent"],
            "model":        "gemini-3.1-flash-lite",
        },
    }

@router.post("/analyze/stream")
async def analyze_stream(req: SurveillanceRequest):
    """
    Streaming version — SSE stream of agent progress and final report.
    """
    try:
        geo = geocode_location(req.location)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    async def event_generator():
        yield json.dumps({"type": "progress", "data": f"Geocoded: {geo['city']}, {geo['country']}"}) + "\n"
        yield json.dumps({"type": "progress", "data": "Fetching weather and AQI data..."}) + "\n"

        weather_snap = fetch_weather_aqi(geo["lat"], geo["lon"], geo["city"])
        yield json.dumps({"type": "weather_snapshot", "data": json.loads(weather_snap)}) + "\n"

        yield json.dumps({"type": "progress", "data": "Dispatching agents..."}) + "\n"

        team = build_team(req.location, geo, req.time_horizon.value)
        loop = asyncio.get_event_loop()

        def run_team():
            resp = team.run(
                f"Execute full health intelligence for {geo['city']}, {geo['country']}. "
                f"Lat={geo['lat']}, Lon={geo['lon']}. "
                f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}. "
                f"Planning Horizon: {req.time_horizon.value}",
                stream=False,
            )
            return resp.content if hasattr(resp, "content") else str(resp)

        yield json.dumps({"type": "progress", "data": "Agents running (this may take 30–60s)..."}) + "\n"
        raw = await loop.run_in_executor(None, run_team)

        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            report = json.loads(clean)
            # Proactively save the intelligence report for the distribution endpoint
            with open(os.path.join(tempfile.gettempdir(), "latest_surveillance.json"), "w") as f:
                json.dump(report, f, indent=2)
        except Exception:
            report = {"raw_output": raw}

        yield json.dumps({"type": "result", "data": report}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@router.get("/snapshot")
def snapshot(location: str):
    """
    Lightweight endpoint — returns only weather + AQI snapshot (no agents).
    """
    try:
        geo = geocode_location(location)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    data = fetch_weather_aqi(geo["lat"], geo["lon"], geo["city"])
    news = fetch_health_news(geo["city"])

    return {
        "location":        geo,
        "weather_aqi":     json.loads(data),
        "health_news":     json.loads(news),
        "snapshot_time":   datetime.utcnow().isoformat() + "Z",
    }

@router.post("/analyze_memory")
async def analyze_memory(req: SurveillanceRequest):
    """
    Run the full 3-agent health surveillance cycle with Cognee historical memory injection.
    Saves the final report back into the Cognee graph.
    """
    try:
        geo = geocode_location(req.location)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Retrieve historical context from Cognee
    memory_context = await retrieve_historical_context(req.location)

    team = build_team(req.location, geo, req.time_horizon.value, memory_context=memory_context)
    loop = asyncio.get_event_loop()

    def run_team():
        response = team.run(
            f"Execute the full health intelligence cycle for: {geo['city']}, {geo['country']}\n"
            f"Coordinates: lat={geo['lat']}, lon={geo['lon']}\n"
            f"Today: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Time Horizon for Planning: {req.time_horizon.value}\n\n"
            "Each agent must gather their domain signals, then the supervisor synthesises everything into the structured JSON report.",
            stream=False,
        )
        return response.content if hasattr(response, "content") else str(response)

    raw = await loop.run_in_executor(None, run_team)

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        report = json.loads(clean)
        
        # Save to memory instead of /tmp
        await save_surveillance_report(req.location, report)
    except Exception:
        report = {"raw_output": raw, "parse_error": "Agent did not return valid JSON or memory save failed."}

    return {
        "location": geo,
        "report":   report,
        "meta": {
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "agents_used":  ["Signal Collector", "Festival Surge Anticipator", "Pollution Risk Agent"],
            "model":        "gemini-3.1-flash-lite",
            "memory_used":  True
        },
    }
