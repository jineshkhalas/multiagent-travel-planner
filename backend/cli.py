import asyncio
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

from typing import List, Dict, Any
from dotenv import load_dotenv
import litellm

# Ensure backend dir is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.weather_agent.agent import get_weather
from agents.attractions_agent.agent import get_attractions
from agents.flights_agent.agent import search_flights
from agents.hotels_agent.agent import search_hotels

# Load .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(env_path)
load_dotenv()

litellm.suppress_debug_info = True

CONTEXT_SYSTEM_PROMPT = """You are a Conversation Memory and Trip Context Resolver.
Your job is to examine the conversation history, existing itinerary (if any), and the latest user message to extract accurate, persistent trip parameters.

RULES:
1. PRESERVE MEMORY: If the user previously mentioned origin (like Ahmedabad) and destination (like Mumbai), and now says "plan it for 5 days by adding lonavala", the source is STILL Ahmedabad, the destinations are ["Mumbai", "Lonavala"], and duration is 5 days.
2. EXTRACT ACCURATELY:
   - "source": Starting city/airport.
   - "destinations": Array of all intended destination cities/places in logical travel order (e.g. ["Mumbai", "Lonavala"]).
   - "duration_days": Total number of days for the trip (e.g. 5). If unspecified or if user asks for a picnic / day trip, set to 1.
   - "is_modification": Boolean indicating if this is modifying/extending a previous plan.
   - "modifications": Summary of what changed.
3. OUTPUT FORMAT: Return strictly a valid JSON object. Do not wrap with markdown code blocks.
"""

FORMATTING_SYSTEM_PROMPT = """You are a master travel planner. Your job is to format and compile the retrieved specialist sub-agent data into a clean, strictly structured, and realistic travel itinerary.

MANDATORY STRUCTURAL RULES:
1. STRICT DESTINATION BOUNDARY: ONLY include activities, spots, and hotels located in the explicitly requested target destinations.
   - ABSOLUTELY NEVER add random distant cities unless explicitly requested!
2. ALL 4 MAIN SECTIONS ARE STRICTLY MANDATORY (NEVER SKIP ANY SECTION):
   - Section 1: ### Flights & Transit Options
   - Section 2: ### Weather Conditions (ALWAYS include this section!)
   - Section 3: ### Recommended Accommodations
   - Section 4: ### Detailed Day-by-Day Itinerary
3. 1-DAY PICNIC / SHORT ROAD TRIP RULES (CRITICAL):
   - If duration is 1 Day OR distance is under 250 km (e.g. Ahmedabad to Dakor, Pune to Matheran):
     * FLIGHTS: Under "#### Flights", write:
       "- **Direct Flights**: Not applicable for this short-distance route (Direct road drive, cab, bus, or local train is recommended)."
       ABSOLUTELY NEVER fabricate commercial airline flights when no commercial airports exist or for short road trips!
     * ACCOMMODATIONS: Under "### Recommended Accommodations", write:
       "- **Same-Day Return**: Not applicable for a 1-day trip (return to [Source] the same evening/night). No overnight hotel stay is required."
     * ITINERARY: Day 1 Evening MUST conclude with buying local snacks/specialties and the return journey back to [Source].
4. MULTI-DAY ITINERARY STRUCTURE:
   - Generate EXACTLY the requested number of days.
   - FOR EVERY SINGLE DAY (Day 1 to Day N), you MUST include all three time blocks:
     - **Morning**: [Activity 1] (Distance: X km | Taxi: ₹X | Entry: ₹X | Food: ₹X) • [Activity 2]
     - **Afternoon**: [Activity 1] (Distance: X km | Taxi: ₹X | Entry: ₹X | Food: ₹X) • [Activity 2]
     - **Evening**: [Activity 1] (Taxi: ₹X | Entry: ₹X) • Dinner at local restaurant (₹X)
     NEVER skip Afternoon or Evening on any day!
5. REALISTIC PRICING SANITY CHECK (CRITICAL):
   - FLIGHTS (for long-distance multi-day trips with airports only): Fares ₹2,500 - ₹8,500.
   - TRAINS: Standard Indian Railways fares range between ₹350 and ₹2,500.
   - HOTELS (for multi-day trips with overnight stays): Put the REAL Hotel Name in bold (e.g. `- **The Imperial, New Delhi**: Janpath | Approx. ₹15,000 / night`).
6. ALL PRICES IN INR (₹):
   - Never use $ symbols. All costs must be in INR (₹).
7. CLEAN HEADERS:
   - Do NOT wrap markdown headers in bold (use `### Flights & Transit Options`, NOT `### **Flights & Transit Options**`).
   - Do NOT output raw emoji characters in headers or text.

STRICT OUTPUT TEMPLATE:

### Flights & Transit Options

#### Flights
- [If 1-Day Trip or short distance: **Direct Flights**: Not applicable for this short-distance route (Direct road drive, cab, bus, or local train is recommended). | If long distance with airports: List up to 3 distinct airlines: - **[Airline 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare] | Duration: [X]h [Y]m]

#### Trains
- **[Train Name & Number 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **[Train Name & Number 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

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
- [If 1-Day Trip: **Same-Day Return**: Not applicable for a 1-day trip (return to [Source] the same evening/night). No overnight hotel stay is required. | If Multi-Day Trip: - **[Hotel Name 1]**: [Location / Highlights] | Approx. ₹[Tariff] / night]

#### Premium / 3-Star & 4-Star Stays (Top 2)
- [If Multi-Day Trip: - **[Hotel Name 1]**: [Location / Highlights] | Approx. ₹[Tariff] / night]

#### Budget & Cheap Stays (Top 2)
- [If Multi-Day Trip: - **[Hotel Name 1]**: [Location / Highlights] | Approx. ₹[Tariff] / night]

### Detailed Day-by-Day Itinerary

For each Day (Day 1 to the final Day):
#### Day X: [City/Region Theme]
- **Morning**: [Activity 1] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
- **Afternoon**: [Activity 1] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
- **Evening**: [Activity 1] (Taxi: ₹[Amount] | Entry: ₹[Amount]) • Dinner at local restaurant (₹[Amount]) [If final day / 1-day trip: • Return journey back to [Source]]
"""

async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Direct LiteLLM call with automatic backoff on rate limits."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    for attempt in range(4):
        try:
            resp = await litellm.acompletion(
                model="groq/llama-3.1-8b-instant",
                messages=messages,
                temperature=0.3
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str or "tokens per minute" in err_str:
                wait_sec = 2.5 * (attempt + 1)
                print(f"[*] Rate limit hit (attempt {attempt+1}/4). Retrying in {wait_sec}s...")
                await asyncio.sleep(wait_sec)
            else:
                print(f"[*] LLM error: {e}")
                break

    return ""

class PlannerFlow:
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
        ctx_response = await call_llm(CONTEXT_SYSTEM_PROMPT, context_prompt)
        
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

        lower_msg = request.lower()
        if "1 day" in lower_msg or "one day" in lower_msg or "picnic" in lower_msg or "day trip" in lower_msg:
            duration_days = 1

        if not destinations or destinations == ["Unknown"]:
            if "dakor" in lower_msg:
                destinations = ["Dakor"]
            elif "taranga" in lower_msg:
                destinations = ["Taranga Hills"]
            elif "delhi" in lower_msg:
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
                destinations = ["Dakor" if "dakor" in lower_msg else "Delhi"]

        if source == "Unknown":
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
        is_day_trip = (duration_days == 1)

        print(f"\n🌍 Trip Context: Source: '{source}', Destinations: {destinations}, Duration: {duration_days} Days (DayTrip: {is_day_trip}), Modification: {is_mod}\n")
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

        # 3. Hotels (Only fetch for multi-day trips)
        if duration_days > 1:
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
- Duration: {duration_days} Day(s) {"(1-DAY SAME-DAY RETURN PICNIC TRIP - NO FLIGHTS & NO HOTELS NEEDED)" if is_day_trip else ""}
- Modification Request: {modifications if is_mod else "New Itinerary"}

PREVIOUS ITINERARY (FOR CONTINUITY IF MODIFYING):
{current_plan if current_plan else "None"}

RAW RETRIEVED SUB-AGENT DATA:
{subagent_text}

USER REQUEST:
{request}

CRITICAL RULES FOR THIS TRIP:
{"1. Since this is a 1-Day picnic trip: State that flights and overnight hotels are NOT applicable (same-day return to " + source + ")." if is_day_trip else "1. Multi-day trip with verified hotels and transit."}
2. Ensure realistic local taxi, entry tickets, and food budgets in INR (₹).
3. Day 1 Evening must include return transit back home to {source} if 1-day trip.
"""
        print("[*] Synthesizing verified, anti-hallucinated itinerary with strict structure...")
        final_itinerary = await call_llm(FORMATTING_SYSTEM_PROMPT, format_context)

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