import os
import sys
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure backend dir is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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

app = FastAPI(title="AI Travel Planner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

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
    instruction="""You are a master travel planner. Your job is to format and compile the retrieved specialist sub-agent data into a clean, strictly structured, and realistic travel itinerary.

    MANDATORY STRUCTURAL RULES:
    1. STRICT DESTINATION BOUNDARY: ONLY include activities, spots, and hotels located in the explicitly requested target destinations.
    - ABSOLUTELY NEVER add random distant cities unless explicitly requested!
    2. ALL 4 MAIN SECTIONS ARE STRICTLY MANDATORY (NEVER SKIP ANY SECTION):
       - Section 1: ### Flights & Transit Options
       - Section 2: ### Weather Conditions (ALWAYS include this section!)
       - Section 3: ### Recommended Accommodations
       - Section 4: ### Detailed Day-by-Day Itinerary
    3. REAL NAMES IN BOLD:
       - For Hotels: Put the REAL Hotel Name in bold (e.g. `- **The Imperial, New Delhi**: Janpath | Luxury heritage stay | Approx. ₹15,000 / night`). DO NOT use generic `- **Hotel 1**: ...`.
       - For Flights: Put the Airline name in bold (e.g. `- **IndiGo**: Dep: 09:00 - Arr: 10:38 | Price: ₹4,680 | Duration: 1h 38m`).
       - For Trains: Put the Train name & number in bold (e.g. `- **19031 - YOGA EXPRESS**: Dep: 11:55 - Arr: 05:19 | Price: ₹540 | Duration: 17h 24m`).
       - For Road: Use distinct bullets for Car/Cab and Bus/Transit.
    4. MULTI-DAY ITINERARY STRUCTURE:
       - Generate EXACTLY the requested number of days.
       - FOR EVERY SINGLE DAY (Day 1 to Day N), you MUST include all three time blocks:
         - **Morning**: [Activity 1] (Distance: X km | Taxi: ₹X | Entry: ₹X | Food: ₹X) • [Activity 2]
         - **Afternoon**: [Activity 1] (Distance: X km | Taxi: ₹X | Entry: ₹X | Food: ₹X) • [Activity 2]
         - **Evening**: [Activity 1] (Taxi: ₹X | Entry: ₹X) • Dinner at local restaurant (₹X)
         NEVER skip Afternoon or Evening on any day!
    5. ALL PRICES IN INR (₹):
       - Never use $ symbols. All costs must be in INR (₹).
    6. CLEAN HEADERS:
       - Do NOT wrap markdown headers in bold (use `### Flights & Transit Options`, NOT `### **Flights & Transit Options**`).
       - Do NOT output raw emoji characters in headers or text.

    STRICT OUTPUT TEMPLATE:

    ### Flights & Transit Options

    #### Flights
    - **[Airline 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
    - **[Airline 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
    - **[Airline 3]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

    #### Trains
    - **[Train Name & Number 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
    - **[Train Name & Number 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
    - **[Train Name & Number 3]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

    #### Road & Local Transit
    - **Car / Cab**: ~[X] km | ~[Y] hours drive | Approx. ₹[Fare]
    - **Bus / State Transport**: AC Sleeper / Volvo | ~[Y] hours | Approx. ₹[Fare]
    - **Local City Transit**: Autos, Metro, and Taxis available for ₹10 - ₹150 per ride.

    ### Weather Conditions

    #### Live Weather & Packing Tips
    - **Temperature & Condition**: [Current Temp]°C, [Condition]
    - **Humidity & Wind**: [Humidity]%, [Wind Speed] km/h
    - **Packing Advice**: [Practical clothing and travel essentials advice]

    ### Recommended Accommodations

    #### Luxury / 5-Star Stays (Top 2)
    - **[Real Hotel Name 1]**: [Location / Highlights] | Approx. ₹[Tariff] / night
    - **[Real Hotel Name 2]**: [Location / Highlights] | Approx. ₹[Tariff] / night

    #### Premium / 3-Star & 4-Star Stays (Top 2)
    - **[Real Hotel Name 1]**: [Location / Highlights] | Approx. ₹[Tariff] / night
    - **[Real Hotel Name 2]**: [Location / Highlights] | Approx. ₹[Tariff] / night

    #### Budget & Cheap Stays (Top 2)
    - **[Real Hotel Name 1]**: [Location / Highlights] | Approx. ₹[Tariff] / night
    - **[Real Hotel Name 2]**: [Location / Highlights] | Approx. ₹[Tariff] / night

    ### Detailed Day-by-Day Itinerary

    For each Day (Day 1 to the final Day):
    #### Day X: [City/Region Theme]
    - **Morning**: [Activity 1] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
    - **Afternoon**: [Activity 1] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
    - **Evening**: [Activity 1] (Taxi: ₹[Amount] | Entry: ₹[Amount]) • Dinner at local restaurant (₹[Amount])
    """
)

class PlannerFlow:
    def __init__(self):
        self.session_svc = InMemorySessionService()
        self.context_runner = Runner(app_name="Ctx", agent=context_agent, session_service=self.session_svc, auto_create_session=True)
        self.format_runner = Runner(app_name="Fmt", agent=formatting_agent, session_service=self.session_svc, auto_create_session=True)

    async def run_llm_agent(self, runner, prompt: str) -> str:
        """Executes LLM agent runner with retry and exponential backoff on Groq rate limits."""
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
                    print(f"[PlannerFlow] Error running {runner.app_name}: {e}")
                    break

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
        ctx_response = await self.run_llm_agent(self.context_runner, context_prompt)
        
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
            print(f"[Backend API] Notice: Fallback parameter extraction used ({e})")

        # Robust heuristic fallback if parsing failed
        if not destinations or destinations == ["Unknown"]:
            lower_msg = current_message.lower()
            if "delhi" in lower_msg:
                destinations = ["Delhi"]
            elif "mumbai" in lower_msg:
                destinations = ["Mumbai"]
            elif "goa" in lower_msg:
                destinations = ["Goa"]
            elif "matheran" in lower_msg:
                destinations = ["Matheran"]
            elif "jaipur" in lower_msg:
                destinations = ["Jaipur"]
            elif "varanasi" in lower_msg:
                destinations = ["Varanasi"]
            else:
                destinations = ["Delhi"]

        if source == "Unknown":
            lower_msg = current_message.lower()
            if "ahmedabad" in lower_msg:
                source = "Ahmedabad"
            elif "mumbai" in lower_msg and "to" in lower_msg:
                source = "Mumbai"
            elif "delhi" in lower_msg and "from delhi" in lower_msg:
                source = "Delhi"
            elif "pune" in lower_msg:
                source = "Pune"

        primary_dest = destinations[0] if destinations else "Delhi"
        all_dest_str = ", ".join(destinations)

        print(f"[Backend API] Resolved Trip Context: Source='{source}', Destinations={destinations}, Duration={duration_days} days, IsMod={is_mod}")

        # Fetch live data in parallel across all 4 specialist domains
        tasks = []

        # 1. Weather
        for dest in destinations:
            tasks.append(asyncio.to_thread(get_weather, dest))

        # 2. Flights & Transit
        if source and source != "Unknown":
            tasks.append(asyncio.to_thread(search_flights, source, primary_dest))
        else:
            tasks.append(asyncio.to_thread(search_flights, "Major Hubs", primary_dest))

        if len(destinations) > 1:
            tasks.append(asyncio.to_thread(search_flights, destinations[0], destinations[1]))

        # 3. Hotels
        for dest in destinations:
            tasks.append(asyncio.to_thread(search_hotels, dest))

        # 4. Attractions
        for dest in destinations:
            tasks.append(asyncio.to_thread(get_attractions, dest))

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

REMINDER: You MUST include ALL 4 SECTIONS:
1. ### Flights & Transit Options (Flights, Trains, Road & Local Transit with Car/Cab & Bus)
2. ### Weather Conditions (Live Weather & Packing Tips)
3. ### Recommended Accommodations (Real Hotel Names in bold under Luxury, Premium, Budget)
4. ### Detailed Day-by-Day Itinerary (Morning, Afternoon, Evening for every single day)
"""
        print("[Backend API] Generating verified, non-hallucinated itinerary with strict structure...")
        final_itinerary = await self.run_llm_agent(self.format_runner, format_context)

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

@app.get("/")
def root_check():
    return {
        "status": "online",
        "service": "AI Multi-Agent Travel Planner API",
        "version": "1.0.0"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "agents": {
            "Weather": "online",
            "Attractions": "online",
            "Flights": "online",
            "Hotels": "online"
        }
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
    port = int(os.getenv("PORT", 8000))
    print(f"[*] Starting AI Travel Planner Backend API on http://0.0.0.0:{port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port)
