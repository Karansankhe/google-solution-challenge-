import json
import os
import glob
from app.core.config import get_settings

from agno.agent import Agent
from agno.models.google import Gemini
from agno.team.team import Team
from agno.tools.reasoning import ReasoningTools

settings = get_settings()

def load_dataset_context() -> str:
    """Loads all CSV files from the dataset directory into a single context string."""
    dataset_dir = r"d:\Users\Desktop\codeforcom\dataset"
    if not os.path.exists(dataset_dir):
        return "No dataset directory found."
    
    csv_files = glob.glob(os.path.join(dataset_dir, "*.csv"))
    context = ""
    for file in csv_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                filename = os.path.basename(file)
                context += f"\n--- Dataset: {filename} ---\n{content}\n"
        except Exception as e:
            context += f"\nError reading {file}: {e}\n"
    
    return context

def build_distribution_team(location: str, surveillance_report, time_horizon: str = "long") -> Team:
    gemini = Gemini(id="gemini-3.1-flash-lite", api_key=settings.GEMINI_API_KEY)

    dataset_context = load_dataset_context()
    
    if isinstance(surveillance_report, dict):
        surveillance_summary = json.dumps(surveillance_report, indent=2)
    else:
        surveillance_summary = str(surveillance_report)

    forecasting_agent = Agent(
        name="Resource Forecasting Agent",
        role="Analyze current medicine, bed, and personnel capacity against the health intelligence report to predict upcoming demand and potential stock-outs.",
        model=gemini,
        instructions=[
            f"Target location: {location}",
            f"Time horizon: {time_horizon}",
            "",
            "SURVEILLANCE INTELLIGENCE REPORT:",
            surveillance_summary,
            "",
            "AVAILABLE DATASETS (Facility capacities, Personnel, etc.):",
            dataset_context,
            "",
            "Your tasks:",
            "1. Analyze the disease outbreak risks, upcoming festivals, and pollution risks from the intelligence report.",
            "2. Cross-reference these risks with the facility and personnel data from the CSVs (e.g., number of PHCs, bed capacity if inferred, doctors/assistants available).",
            "3. Forecast which specific resources (e.g., respiratory medicines, emergency beds, trauma kits) will experience the highest demand.",
            "4. Identify potential stock-out or personnel shortage locations.",
            "5. Produce a structured demand forecast.",
        ],
        add_datetime_to_context=True,
    )

    supply_chain_agent = Agent(
        name="Supply Chain & Redistribution Agent",
        role="Formulate proactive cross-district resource redistribution recommendations based on forecasts.",
        model=gemini,
        instructions=[
            f"Target location: {location}",
            "",
            "SURVEILLANCE INTELLIGENCE REPORT:",
            surveillance_summary,
            "",
            "AVAILABLE DATASETS (Facility capacities, Personnel, etc.):",
            dataset_context,
            "",
            "Your tasks:",
            "1. Identify regions/districts with surplus resources and those with predicted deficits based on the forecasting agent's findings.",
            "2. Propose automated cross-district resource redistribution (e.g., move 20% of buffer stock from District A to District B).",
            "3. Formulate logistics and supply chain alerts for local health officials.",
            "4. Focus on proactive measures rather than reactive.",
        ],
        add_datetime_to_context=True,
    )

    supervisor = Team(
        name="Distribution & Supply Chain Supervisor",
        mode="coordinate",
        model=gemini,
        members=[forecasting_agent, supply_chain_agent],
        tools=[ReasoningTools(add_instructions=True)],
        instructions=[
            f"You are the Supply Chain & Distribution Supervisor for: {location}.",
            "",
            "WORKFLOW:",
            "1. Dispatch the Resource Forecasting Agent to predict demand and shortages.",
            "2. Dispatch the Supply Chain & Redistribution Agent to plan logistics and transfers.",
            "3. Synthesise both outputs into a comprehensive distribution plan JSON.",
            "",
            "OUTPUT FORMAT (strict JSON — no extra prose outside the JSON block):",
            """
{
  "location": "...",
  "generated_at": "ISO8601",
  "demand_forecast": {
    "high_risk_areas": ["..."],
    "predicted_shortages": [
      { "item": "...", "area": "...", "expected_deficit": "...", "reason": "..." }
    ]
  },
  "redistribution_plan": {
    "transfers": [
      { "from_location": "...", "to_location": "...", "resource_type": "...", "quantity": "...", "urgency": "..." }
    ],
    "logistics_alerts": ["..."]
  },
  "recommended_procurement": ["..."]
}
""",
            "Respond ONLY with valid JSON. No markdown, no preamble."
        ],
        markdown=False,
        show_members_responses=False,
        add_datetime_to_context=True,
    )

    return supervisor
