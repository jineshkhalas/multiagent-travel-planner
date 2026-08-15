import asyncio
import json
import os
import sys
from typing import List, Dict, Any
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
    instruction="""You are a master travel planner. Your job is to format and compile the specialist sub-agent data into a clean, strictly structured, and realistic travel itinerary.

CRITICAL RULES:
1. STRICT DESTINATION BOUNDARY: ONLY include activities, spots, and hotels located in the explicitly requested target destinations.
   - ABSOLUTELY NEVER add random distant cities unless explicitly requested!
2. MULTI-DAY ITINERARY STRUCTURE:
   - Generate EXACTLY the requested number of days.
   - FOR EVERY SINGLE DAY (Day 1 to Day N), you MUST include all three time blocks:
     - **Morning**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Activity 2]
     - **Afternoon**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Activity 2]
     - **Evening**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Dinner / Leisure: ₹]
     NEVER skip Afternoon or Evening on any day!
3. FLIGHTS & TRAINS STRUCTURE:
   - Under "#### Flights", list up to 3 distinct flight options formatted as:
     - **Flight 1**: [Airline Name] | Departure: [Time] & Arrival: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
     - **Flight 2**: [Airline Name] | Departure: [Time] & Arrival: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
     - **Flight 3**: [Airline Name] | Departure: [Time] & Arrival: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
   - Under "#### Trains", list up to 3 distinct train options formatted as:
     - **Train 1**: [Train Name & Number] | Departure: [Time] & Arrival: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
     - **Train 2**: [Train Name & Number] | Departure: [Time] & Arrival: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
     - **Train 3**: [Train Name & Number] | Departure: [Time] & Arrival: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
   - Under "#### Road & Local Transit", provide estimated road distance, drive time, and cab fare in ₹.
4. HOTEL TIERS (EXACTLY 2 HOTELS PER CATEGORY):
   - Under "#### Luxury / 5-Star / 7-Star Stays (Top 2)": List 2 real hotels with nightly tariff in ₹.
   - Under "#### Premium / 3-Star & 4-Star Stays (Top 2)": List 2 real hotels with nightly tariff in ₹.
   - Under "#### Budget & Cheap Stays (Top 2)": List 2 real hotels with nightly tariff in ₹.
5. WEATHER & PACKING:
   - Bullet points with Temperature, Condition, Humidity, Wind, and practical packing advice (clothing/essentials).
6. ALL PRICES IN INR (₹):
   - Never use $ symbols. All costs must be in INR (₹).
7. NO RAW EMOJIS:
   - Do NOT output raw emoji characters (like ✈️, 🌤️, 🏨, 🗺️, 🌅, 🌇, 🚕). Use clean markdown headers so the frontend UI can render vector icons automatically.

STRICT OUTPUT TEMPLATE:

### Flights & Transit Options
#### Flights
- **Flight 1**: [Airline] | Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **Flight 2**: [Airline] | Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **Flight 3**: [Airline] | Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

#### Trains
- **Train 1**: [Train Name & Number] | Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **Train 2**: [Train Name & Number] | Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **Train 3**: [Train Name & Number] | Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

#### Road & Local Transit
- Road Distance: ~[X] km | Estimated Drive Time: ~[Y] hours | Typical Cab Fare: ₹[Amount]

### Weather Conditions
#### Live Weather & Packing Tips
- **Temperature & Condition**: [Current Temp]°C, [Condition]
- **Humidity & Wind**: [Humidity]%, [Wind Speed] km/h
- **Packing Advice**: [Practical clothing & travel essentials advice]

### Recommended Accommodations
#### Luxury / 5-Star / 7-Star Stays (Top 2)
- **Hotel 1**: [Hotel Name] | [Key Highlight/Location] | Approx. ₹[Tariff] / night
- **Hotel 2**: [Hotel Name] | [Key Highlight/Location] | Approx. ₹[Tariff] / night

#### Premium / 3-Star & 4-Star Stays (Top 2)
- **Hotel 1**: [Hotel Name] | [Key Highlight/Location] | Approx. ₹[Tariff] / night
- **Hotel 2**: [Hotel Name] | [Key Highlight/Location] | Approx. ₹[Tariff] / night

#### Budget & Cheap Stays (Top 2)
- **Hotel 1**: [Hotel Name] | [Key Highlight/Location] | Approx. ₹[Tariff] / night
- **Hotel 2**: [Hotel Name] | [Key Highlight/Location] | Approx. ₹[Tariff] / night

### Detailed Day-by-Day Itinerary
For each Day (Day 1 to the final Day):
#### Day X: [City/Region Theme]
- **Morning**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Activity 2]
- **Afternoon**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Activity 2]
- **Evening**: [Activity 1] (Distance | Transport: ₹ | Entry: ₹ | Food: ₹) • [Dinner / Leisure: ₹]
"""
)

class PlannerFlow:
    def __init__(self):
        self.session_svc = InMemorySessionService()
        self.context_runner = Runner(app_name="Ctx", agent=context_agent, session_service=self.session_svc, auto_create_session=True)
        self.format_runner = Runner(app_name="Fmt", agent=formatting_agent, session_service=self.session_svc, auto_create_session=True)

    async def run_llm_agent(self, runner, prompt: str) -> str:
        """Runs agent runner with retry on rate limits."""
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        
        for attempt in range(4):
            try:
                async for event in runner.run_async(user_id="cli", session_id=f"sess_{os.urandom(4).hex()}", new_message=message):
                    if hasattr(event, 'is_final_response') and event.is_final_response():
                        if event.content and event.content.parts:
                            return event.content.parts[0].text
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str or "429" in err_str or "tokens per minute" in err_str:
                    wait_sec = 2.5 * (attempt + 1)
                    print(f"[*] Rate limit on {runner.app_name} (attempt {attempt+1}/4). Retrying in {wait_sec}s...")
                    await asyncio.sleep(wait_sec)
                else:
                    print(f"[*] Error running {runner.app_name}: {e}")
                    break

        return "Data unavailable"

    async def run(self, request: str, history: List[Dict[str, str]] = None, current_plan: str = ""):
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
{request}

Extract and resolve persistent trip parameters (source, destinations list, duration_days, is_modification, modifications). Return JSON only.
"""
        print("[System] Resolving trip context with conversation memory...")
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
            print(f"[System] Notice: JSON extraction used fallback.")

        if not destinations or destinations == ["Unknown"]:
            lower_msg = request.lower()
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
            lower_msg = request.lower()
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

        print(f"\n🌍 Trip Context: Source: '{source}', Destinations: {destinations}, Duration: {duration_days} Days, Modification: {is_mod}\n")
        print(f"[*] Querying Specialist Agents for {all_dest_str}...")

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
{request}
"""
        print("[*] Synthesizing verified, anti-hallucinated itinerary with strict structure...")
        final_itinerary = await self.run_llm_agent(self.format_runner, format_context)

        return {
            "source": source,
            "destination": all_dest_str,
            "destinations": destinations,
            "duration_days": duration_days,
            "itinerary": final_itinerary
        }

async def main():
    flow = PlannerFlow()
    history = []
    current_plan = ""

    print("==================================================")
    print("🌍 AI Travel Planner (A2A Architecture CLI)")
    print("Type your trip request (e.g. 'Plan a 3 day trip to Mumbai from Ahmedabad')")
    print("Type 'exit' to quit.")
    print("==================================================\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            result = await flow.run(user_input, history=history, current_plan=current_plan)
            itinerary = result["itinerary"]
            current_plan = itinerary

            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": itinerary[:300] + "..."})

            print("\n" + "="*50)
            print("🗺️ MULTI-AGENT ITINERARY")
            print("="*50 + "\n")
            print(itinerary)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

if __name__ == "__main__":
    asyncio.run(main())