import os
import sys
import json
import asyncio
import requests
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure backend dir is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.weather_agent.agent import get_weather
from agents.attractions_agent.agent import get_attractions
from agents.flights_agent.agent import search_flights
from agents.hotels_agent.agent import search_hotels

# Load .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(env_path)
load_dotenv()

app = FastAPI(title="AI Travel Planner A2A API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_agent_card_path(port: int, name: str) -> str:
    file_path = os.path.join(os.path.dirname(__file__), f"fixed_card_{port}.json")
    if os.path.exists(file_path):
        return file_path
    
    try:
        url = f"http://127.0.0.1:{port}/.well-known/agent-card.json"
        card_data = requests.get(url, timeout=3).json()
        card_data["supportedInterfaces"][0]["url"] = f"http://127.0.0.1:{port}"
        with open(file_path, "w") as f:
            json.dump(card_data, f)
        return file_path
    except Exception as e:
        print(f"[Server] Warning: Could not fetch live card for {name} on port {port}: {e}")
        return file_path

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

weather_sub = RemoteA2aAgent(name="WeatherRemote", agent_card=get_agent_card_path(8001, "Weather"))
attractions_sub = RemoteA2aAgent(name="AttractionsRemote", agent_card=get_agent_card_path(8002, "Attractions"))
flights_sub = RemoteA2aAgent(name="FlightsRemote", agent_card=get_agent_card_path(8003, "Flights"))
hotels_sub = RemoteA2aAgent(name="HotelsRemote", agent_card=get_agent_card_path(8004, "Hotels"))

context_agent = LlmAgent(
    name="ContextResolverAgent",
    model=groq_model,
    instruction="""You are a Conversation Memory and Trip Context Resolver.
    Your job is to examine the entire conversation history, existing itinerary (if any), and the latest user message to extract accurate, persistent trip parameters.

    RULES:
    1. PRESERVE MEMORY: If the user previously mentioned origin (like Ahmedabad) and destination (like Mumbai), and now says "plan it for 5 days by adding lonavala", the source is STILL Ahmedabad, the destinations are ["Mumbai", "Lonavala"], and duration is 5 days.
    2. EXTRACT ACCURATELY:
    - "source": Starting city/airport.
    - "destinations": Array of all intended destination cities/places in logical travel order (e.g. ["Mumbai", "Lonavala"]).
    - "duration_days": Total number of days for the trip (e.g. 5). If unspecified, default to 3.
    - "is_modification": Boolean indicating if this is modifying/extending a previous plan.
    - "modifications": Summary of what changed.
    3. OUTPUT FORMAT: Return strictly a valid JSON object. Do not wrap with markdown code blocks.
    """
)

formatting_agent = LlmAgent(
    name="FormattingAgent",
    model=groq_model,
    instruction="""You are a master travel planner. Your job is to format and compile the specialist sub-agent data into a crisp, cohesive, and realistic travel itinerary.

    CRITICAL ANTI-HALLUCINATION & GEOGRAPHIC RULES:
    1. STRICT DESTINATION BOUNDARY: ONLY include activities, spots, and hotels located in the explicitly requested target destinations.
    - ABSOLUTELY NEVER add random distant cities (e.g. Udaipur, Agra, Delhi, Jaipur, Chennai, Goa) unless explicitly in the user's requested destinations!
    - Transit must be realistic (e.g. Mumbai to Lonavala is ~85 km by train/cab, NOT 1400 km).
    2. MULTI-DAY ITINERARY STRUCTURE:
    - Generate EXACTLY the requested number of days.
    - Divide days logically between the destinations.
    - If this is a modification of a previous plan, maintain continuity for the original days and seamlessly blend in the new days.
    3. ALL PRICES IN INR (₹):
    - All flight fares, train tickets, hotel tariffs, activity fees, and meal budgets MUST be strictly formatted in INR (₹). Never use $ symbols.
    4. NO EMOJIS IN HEADERS OR TEXT:
    - Do NOT output raw emoji characters (like ✈️, 🌤️, 🏨, 🗺️, 🌅, 🌇, 🚕). Use clean markdown section headers so the frontend UI can render Lucide vector icons automatically.

    OUTPUT FORMAT:

    ### Flights & Transit Options
    - Origin to Destination transit (Airlines, Schedules, Fares in ₹)
    - Inter-city transit between destinations (Train / Cab / Expressway details with fare in ₹)

    ### Weather Conditions
    - Bullet points for each destination with live temperature, condition, humidity, and packing tips.

    ### Recommended Accommodations
    - Real hotel recommendations for each destination city with price per night in ₹.

    ### Detailed Day-by-Day Itinerary
    For each Day (Day 1 to the final Day):
    - **Day X: [City/Region Theme]**
    - **Morning**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Activity 2]
    - **Afternoon**: [Activity 1] • [Activity 2]
    - **Evening**: [Activity 1] • [Activity 2]

    Keep descriptions concise, accurate, and completely grounded in the retrieved subagent data.
    """
)

class PlannerFlow:
    def __init__(self):
        self.session_svc = InMemorySessionService()
        self.context_runner = Runner(app_name="Ctx", agent=context_agent, session_service=self.session_svc, auto_create_session=True)
        self.format_runner = Runner(app_name="Fmt", agent=formatting_agent, session_service=self.session_svc, auto_create_session=True)
        self.weather_runner = Runner(app_name="Wth", agent=weather_sub, session_service=self.session_svc, auto_create_session=True)
        self.attr_runner = Runner(app_name="Attr", agent=attractions_sub, session_service=self.session_svc, auto_create_session=True)
        self.flight_runner = Runner(app_name="Flt", agent=flights_sub, session_service=self.session_svc, auto_create_session=True)
        self.hotel_runner = Runner(app_name="Htl", agent=hotels_sub, session_service=self.session_svc, auto_create_session=True)

    async def run_agent(self, runner, prompt: str, fallback_func=None, *fallback_args) -> str:
        """Executes an agent runner with retry on rate limits and automatic fallback to direct tools."""
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        
        for attempt in range(4):
            try:
                async for event in runner.run_async(user_id="web", session_id=f"sess_{os.urandom(4).hex()}", new_message=message):
                    if hasattr(event, 'is_final_response') and event.is_final_response():
                        if event.content and event.content.parts:
                            return event.content.parts[0].text
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str or "429" in err_str or "tokens per minute" in err_str:
                    wait_sec = 2.5 * (attempt + 1)
                    print(f"[PlannerFlow] Rate limit on {runner.app_name} (attempt {attempt+1}/4). Retrying in {wait_sec}s...")
                    await asyncio.sleep(wait_sec)
                else:
                    print(f"[PlannerFlow] Error running runner {runner.app_name}: {e}")
                    break

        # Fallback to direct Python tool if available
        if fallback_func:
            try:
                print(f"[PlannerFlow] Invoking direct tool fallback for {runner.app_name}...")
                return await asyncio.to_thread(fallback_func, *fallback_args)
            except Exception as fe:
                print(f"[PlannerFlow] Direct tool fallback failed: {fe}")

        return "Data unavailable"

    async def run(self, current_message: str, history: List[Dict[str, Any]] = None, current_plan: str = ""):
        history_formatted = ""
        if history:
            for turn in history[-6:]:
                role = "User" if turn.get("role") == "user" else "Assistant"
                content = turn.get("content", "")
                if role == "Assistant" and len(content) > 300:
                    content = content[:300] + "... [existing itinerary]"
                history_formatted += f"{role}: {content}\n"

        context_prompt = f"""
CONVERSATION HISTORY:
{history_formatted if history_formatted else "No previous history."}

CURRENT SAVED ITINERARY SUMMARY:
{current_plan[:400] if current_plan else "No previous itinerary."}

NEW USER MESSAGE:
{current_message}

Extract and resolve the persistent trip parameters (source, destinations list, duration_days, is_modification, modifications). Return JSON only.
"""
        print(f"\n[Backend API] Resolving context with memory...")
        ctx_response = await self.run_agent(self.context_runner, context_prompt)
        
        source = "Unknown"
        destinations = []
        duration_days = 3
        is_mod = False
        modifications = ""

        try:
            clean_json = ctx_response.replace("```json", "").replace("```", "").strip()
            start_idx = clean_json.find('{')
            end_idx = clean_json.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                clean_json = clean_json[start_idx:end_idx]
            
            parsed = json.loads(clean_json)
            source = parsed.get("source", "Unknown")
            raw_dest = parsed.get("destinations", [])
            if isinstance(raw_dest, list):
                destinations = [d for d in raw_dest if d and d != "Unknown"]
            elif isinstance(raw_dest, str) and raw_dest != "Unknown":
                destinations = [d.strip() for d in raw_dest.split(",")]
            
            duration_days = parsed.get("duration_days", 3)
            is_mod = parsed.get("is_modification", False)
            modifications = parsed.get("modifications", "")
        except Exception as e:
            print(f"[Backend API] Warning: Failed to parse context JSON ({e}), fallback extraction...")

        # Rule-based fallback if parsing fails
        if not destinations or destinations == ["Unknown"]:
            lower_msg = current_message.lower()
            if "delhi" in lower_msg:
                destinations = ["Delhi"]
            elif "mumbai" in lower_msg:
                destinations = ["Mumbai"]
            elif "goa" in lower_msg:
                destinations = ["Goa"]
            else:
                destinations = ["Delhi"]

        if source == "Unknown":
            lower_msg = current_message.lower()
            if "ahmedabad" in lower_msg:
                source = "Ahmedabad"
            elif "mumbai" in lower_msg and "to delhi" in lower_msg:
                source = "Mumbai"

        primary_dest = destinations[0] if destinations else "Delhi"
        all_dest_str = ", ".join(destinations)

        print(f"[Backend API] Resolved Trip Context: Source='{source}', Destinations={destinations}, Duration={duration_days} days, IsMod={is_mod}")

        tasks = []

        # Weather tasks with direct fallback
        for dest in destinations:
            tasks.append(self.run_agent(
                self.weather_runner, 
                f"What is the live weather forecast in {dest}?",
                get_weather,
                dest
            ))
        
        # Flight & transit tasks with direct fallback
        if source and source != "Unknown":
            tasks.append(self.run_agent(
                self.flight_runner, 
                f"Find real flight and train options from {source} to {primary_dest} with prices in INR.",
                search_flights,
                source,
                primary_dest
            ))
        else:
            tasks.append(self.run_agent(
                self.flight_runner, 
                f"Find popular flight routes and transit options to {primary_dest}.",
                search_flights,
                "Major Hubs",
                primary_dest
            ))
        
        if len(destinations) > 1:
            tasks.append(self.run_agent(
                self.flight_runner, 
                f"Find transit options, cabs, buses, and trains between {destinations[0]} and {destinations[1]} with travel time and fares.",
                search_flights,
                destinations[0],
                destinations[1]
            ))

        # Hotels tasks with direct fallback
        for dest in destinations:
            tasks.append(self.run_agent(
                self.hotel_runner, 
                f"Find real named hotels, boutique stays, and resorts in {dest} with prices in INR (₹).",
                search_hotels,
                dest
            ))

        # Attractions tasks with direct fallback
        for dest in destinations:
            tasks.append(self.run_agent(
                self.attr_runner, 
                f"Give me top attractions, sightseeing spots, ticket fees, local transport costs, and food spots in {dest}.",
                get_attractions,
                dest
            ))

        subagent_results = await asyncio.gather(*tasks, return_exceptions=True)
        subagent_text = "\n---\n".join([str(r) for r in subagent_results if not isinstance(r, Exception)])

        format_context = f"""
TARGET TRIP PARAMETERS:
- Origin/Source: {source}
- Target Destinations ONLY: {all_dest_str} (STRICT: Do NOT include any other cities!)
- Duration: {duration_days} Days
- Modification Request: {modifications if is_mod else "New Itinerary"}

PREVIOUS ITINERARY (FOR CONTINUITY IF MODIFYING):
{current_plan if current_plan else "None"}

RAW RETRIEVED SUB-AGENT DATA:
{subagent_text}

USER REQUEST:
{current_message}
"""
        print("[Backend API] Generating verified, non-hallucinated itinerary...")
        final_itinerary = await self.run_agent(self.format_runner, format_context)

        return {
            "source": source,
            "destination": all_dest_str,
            "destinations": destinations,
            "duration_days": duration_days,
            "itinerary": final_itinerary
        }

planner = PlannerFlow()

class ChatRequest(BaseModel):
    message: str
    tripId: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    currentPlan: Optional[str] = None

@app.get("/api/health")
def health_check():
    status = {}
    for port, name in [(8001, "Weather"), (8002, "Attractions"), (8003, "Flights"), (8004, "Hotels")]:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/.well-known/agent-card.json", timeout=1)
            status[name] = "online" if r.status_code == 200 else "error"
        except Exception:
            status[name] = "offline"
    return {
        "status": "online",
        "agents": status
    }

@app.post("/api/plan")
async def create_plan(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        result = await planner.run(
            current_message=payload.message,
            history=payload.history or [],
            current_plan=payload.currentPlan or ""
        )
        return {
            "status": "success",
            "source": result["source"],
            "destination": result["destination"],
            "destinations": result.get("destinations", []),
            "duration_days": result.get("duration_days", 3),
            "itinerary": result["itinerary"],
            "reply": result["itinerary"]
        }
    except Exception as e:
        print(f"[Backend API] Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Travel Planner Backend API on http://127.0.0.1:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
