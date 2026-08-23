import json
import os
import tempfile
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models.distribution import DistributionPlanRequest, DistributionPlanResponse
from app.services.distribution import build_distribution_team
from app.services.memory import retrieve_historical_context

router = APIRouter(tags=["Distribution"])

@router.post("/plan", response_model=DistributionPlanResponse)
async def create_distribution_plan(req: DistributionPlanRequest):
    """
    Generate a proactive distribution and resource redistribution plan based on 
    the latest surveillance intelligence and the provided PHC datasets.
    """
    surveillance_file = os.path.join(tempfile.gettempdir(), "latest_surveillance.json")
    
    if not os.path.exists(surveillance_file):
        raise HTTPException(
            status_code=400, 
            detail="Surveillance intelligence report not found. Please run the /api/v1/surveillance/analyze endpoint first."
        )

    try:
        with open(surveillance_file, "r") as f:
            surveillance_report = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading surveillance report: {str(e)}")

    team = build_distribution_team(
        location=req.location,
        surveillance_report=surveillance_report,
        time_horizon=req.time_horizon
    )

    loop = asyncio.get_event_loop()

    def run_team():
        response = team.run(
            f"Execute the supply chain and distribution planning for {req.location}. "
            f"Time horizon: {req.time_horizon}. "
            f"Use the surveillance intelligence and dataset context to forecast demand and plan redistribution.",
            stream=False
        )
        return response.content if hasattr(response, "content") else str(response)

    raw_response = await loop.run_in_executor(None, run_team)

    try:
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        plan_data = json.loads(clean)
    except Exception:
        plan_data = {"raw_output": raw_response, "parse_error": "Agent did not return valid JSON"}

    return DistributionPlanResponse(
        status="success",
        plan=plan_data,
        meta={
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "agents_used": ["Resource Forecasting Agent", "Supply Chain & Redistribution Agent"],
            "model": "gemini-3.1-flash-lite"
        }
    )

@router.post("/plan_memory", response_model=DistributionPlanResponse)
async def create_distribution_plan_memory(req: DistributionPlanRequest):
    """
    Generate a distribution plan by retrieving the latest surveillance intelligence
    from the Cognee memory graph instead of the local filesystem.
    """
    # Retrieve intelligence from memory
    surveillance_report_text = await retrieve_historical_context(
        req.location, 
        query=f"Latest surveillance intelligence report for {req.location}"
    )
    
    if "No historical memory found" in surveillance_report_text:
        raise HTTPException(
            status_code=400, 
            detail="Surveillance intelligence report not found in memory. Please run the /api/v1/surveillance/analyze_memory endpoint first."
        )

    team = build_distribution_team(
        location=req.location,
        surveillance_report=surveillance_report_text,
        time_horizon=req.time_horizon
    )

    loop = asyncio.get_event_loop()

    def run_team():
        response = team.run(
            f"Execute the supply chain and distribution planning for {req.location}. "
            f"Time horizon: {req.time_horizon}. "
            f"Use the surveillance intelligence and dataset context to forecast demand and plan redistribution.",
            stream=False
        )
        return response.content if hasattr(response, "content") else str(response)

    raw_response = await loop.run_in_executor(None, run_team)

    try:
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        plan_data = json.loads(clean)
    except Exception:
        plan_data = {"raw_output": raw_response, "parse_error": "Agent did not return valid JSON"}

    return DistributionPlanResponse(
        status="success",
        plan=plan_data,
        meta={
            "requested_at": datetime.utcnow().isoformat() + "Z",
            "agents_used": ["Resource Forecasting Agent", "Supply Chain & Redistribution Agent"],
            "model": "gemini-3.1-flash-lite",
            "memory_used": True
        }
    )

