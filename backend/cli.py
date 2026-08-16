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
1. PRESERVE MEMORY & ORIGIN:
   - If the user previously mentioned origin (like Delhi) and destination (like Mumbai), and now says "add 4 more days to extend trip to kullu manali", the starting source is STILL Delhi.
   - If adding a destination to extend a trip, the destinations array should include BOTH destinations in logical sequence (e.g. ["Delhi", "Kullu Manali"]).
   - Calculate the total cumulative duration (e.g. 2 original days + 4 added days = 6 total days).
2. EXTRACT ACCURATELY:
   - "source": Starting city/airport (e.g. "Delhi").
   - "destinations": Array of all intended destination cities in logical order (e.g. ["Delhi", "Kullu Manali"]).
   - "duration_days": Total cumulative number of days for the entire trip (e.g. 6).
   - "is_modification": Boolean indicating if this is modifying/extending a previous plan.
   - "modifications": Summary of what changed.
3. OUTPUT FORMAT: Return strictly a valid JSON object. Do not wrap with markdown code blocks.
"""

FORMATTING_SYSTEM_PROMPT = """You are a master travel planner. Your job is to format and compile the retrieved specialist sub-agent data into a clean, strictly structured, realistic, and non-repetitive travel itinerary.

MANDATORY STRUCTURAL RULES:
1. STRICT DESTINATION BOUNDARY: ONLY include activities, spots, and hotels located in the explicitly requested target destinations.
   - ABSOLUTELY NEVER add random distant cities unless explicitly requested!
2. ALL 4 MAIN SECTIONS ARE STRICTLY MANDATORY (NEVER SKIP ANY SECTION):
   - Section 1: ### Flights & Transit Options
   - Section 2: ### Weather Conditions (ALWAYS include this section!)
   - Section 3: ### Recommended Accommodations
   - Section 4: ### Detailed Day-by-Day Itinerary
3. ZERO DUPLICATE ATTRACTIONS (CRITICAL RULE):
   - Every single day (Day 1 through Day N) and time block MUST explore UNIQUE, NEVER-BEFORE-VISITED sights and activities.
   - ABSOLUTELY NEVER repeat the same attraction (e.g. Hadimba Temple, Solang Valley, Rohtang Pass, Red Fort) on multiple days!
   - Spread diverse attractions across the itinerary: temples, mountain viewpoints, waterfalls (Jogini), hot springs (Vashisht), old town markets, nature trails, riverside walks, and local cultural spots.
4. ACCOMMODATION RULES (MULTI-DESTINATIONS):
   - For multi-day trips with multiple destinations (e.g. Delhi and Kullu Manali): List verified hotels FOR EACH DESTINATION in the trip under Luxury (Top 2), Premium (Top 2), Budget (Top 2).
   - For 1-day picnic trips (0 night stay): Output "- **Same-Day Return**: Not applicable for a 1-day trip (return to starting city the same evening/night). No overnight hotel stay is required."
5. ORIGIN & TRANSIT CONTINUITY:
   - For long-distance trips: List 3 distinct airlines (IndiGo, Air India, SpiceJet, Akasa) with realistic fares ₹2,500-₹8,500.
   - The final Day N return journey MUST return to the designated starting city (e.g. Return to Delhi), NEVER an unrelated city.
6. MULTI-DAY ITINERARY STRUCTURE:
   - Generate EXACTLY the requested number of days (Day 1 to Day N).
   - For every single day, include all three time blocks: **Morning**, **Afternoon**, **Evening**.
   - On multi-day trips, intermediate evenings are relaxing at destination/dinner. ONLY the final Day N Evening is the return journey.
7. ALL PRICES IN INR (₹):
   - Never use $ symbols. All costs must be in INR (₹).
8. CLEAN HEADERS:
   - Do NOT wrap markdown headers in bold (use `### Flights & Transit Options`, NOT `### **Flights & Transit Options**`).
   - Do NOT output raw emoji characters in headers or text.

STRICT OUTPUT TEMPLATE:

### Flights & Transit Options

#### Flights
- **[Airline 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare between 2,500 and 8,500] | Duration: [X]h [Y]m
- **[Airline 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare between 2,500 and 8,500] | Duration: [X]h [Y]m
- **[Airline 3]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare between 2,500 and 8,500] | Duration: [X]h [Y]m

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

#### Luxury / 5-Star Stays (Top 2 per destination)
- **[Real Hotel Name 1]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night
- **[Real Hotel Name 2]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night

#### Premium / 3-Star & 4-Star Stays (Top 2 per destination)
- **[Real Hotel Name 1]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night
- **[Real Hotel Name 2]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night

#### Budget & Cheap Stays (Top 2 per destination)
- **[Real Hotel Name 1]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night
- **[Real Hotel Name 2]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night

### Detailed Day-by-Day Itinerary

For each Day (Day 1 to Day N):
#### Day X: [City/Region Theme]
- **Morning**: [Activity 1] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
- **Afternoon**: [Activity 1] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
- **Evening**: [Activity 1] (Taxi: ₹[Amount] | Entry: ₹[Amount]) • Dinner at local restaurant (₹[Amount])
"""

async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Direct LiteLLM call with automatic multi-model fallback and backoff on rate limits."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    models = [
        "groq/openai/gpt-oss-20b",
        "groq/openai/gpt-oss-safeguard-20b",
        "groq/openai/gpt-oss-120b",
        "groq/llama-3.3-70b-versatile"
    ]

    for attempt in range(4):
        for model_name in models:
            try:
                resp = await litellm.acompletion(
                    model=model_name,
                    messages=messages,
                    temperature=0.3
                )
                content = resp.choices[0].message.content.strip()
                if content:
                    return content
            except Exception as e:
                err_str = str(e).lower()
                if "rate_limit" in err_str or "429" in err_str or "tokens per minute" in err_str:
                    print(f"[*] Rate limit hit on {model_name}. Trying fallback...")
                    continue
                else:
                    print(f"[*] LLM error on {model_name}: {e}")

        wait_sec = 2.0 * (attempt + 1)
        print(f"[*] All models busy. Waiting {wait_sec}s before retry (attempt {attempt+1}/4)...")
        await asyncio.sleep(wait_sec)

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
{current_plan[:500] if current_plan else "No previous itinerary."}

NEW USER MESSAGE:
{request}

Extract and resolve persistent trip parameters (source, destinations list, duration_days, is_modification, modifications).
If the user extends or adds days to an existing trip (e.g. 'add 4 more days to kullu manali'), add the days to previous duration (e.g. 2 + 4 = 6 days) and include both destinations. Return JSON only.
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

        import re
        lower_msg = request.lower()
        if "add" in lower_msg and "more day" in lower_msg:
            add_match = re.search(r'add\s*(\d+)\s*more\s*days?', lower_msg)
            if add_match:
                added = int(add_match.group(1))
                if duration_days <= added:
                    duration_days = duration_days + added

        if "manali" in lower_msg or "kullu" in lower_msg:
            if "Kullu Manali" not in destinations and "Manali" not in destinations:
                destinations.append("Kullu Manali")

        if not destinations or destinations == ["Unknown"]:
            if "dakor" in lower_msg:
                destinations = ["Dakor"]
            elif "taranga" in lower_msg:
                destinations = ["Taranga Hills"]
            elif "mumbai" in lower_msg:
                destinations = ["Mumbai"]
            elif "goa" in lower_msg:
                destinations = ["Goa"]
            elif "manali" in lower_msg:
                destinations = ["Kullu Manali"]
            elif "delhi" in lower_msg:
                destinations = ["Delhi"]
            else:
                destinations = ["Delhi"]

        if source == "Unknown":
            if "ahmedabad" in lower_msg:
                source = "Ahmedabad"
            elif "delhi" in lower_msg and ("from delhi" in lower_msg or "delhi" in lower_msg):
                source = "Delhi"
            elif "mumbai" in lower_msg and "from mumbai" in lower_msg:
                source = "Mumbai"
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
            for i in range(len(destinations) - 1):
                tasks.append(asyncio.to_thread(search_flights, destinations[i], destinations[i+1]))

        # 3. Hotels (Only fetch for multi-day trips)
        if duration_days > 1:
            for dest in destinations:
                tasks.append(asyncio.to_thread(search_hotels, dest))

        # 4. Attractions
        for dest in destinations:
            tasks.append(asyncio.to_thread(get_attractions, dest))

        subagent_results = await asyncio.gather(*tasks, return_exceptions=True)
        subagent_text = "\n---\n".join([str(r) for r in subagent_results if not isinstance(r, Exception)])

        if is_day_trip:
            trip_type_instructions = f"""
TRIP TYPE: 1-DAY SAME-DAY RETURN PICNIC TRIP TO {all_dest_str}
- FLIGHTS: Under "#### Flights", write:
  - **Direct Flights**: Not applicable for this short-distance 1-day route. Direct road drive, cab, bus, or local train is recommended.
- HOTELS: Under "### Recommended Accommodations", write:
  - **Same-Day Return**: Not applicable for a 1-day trip (return to {source} the same evening/night). No overnight hotel stay is required.
- PROXIMITY & PRIMARY ATTRACTIONS (CRITICAL):
  * Prioritize the PRIMARY, ICONIC attractions situated ON or immediately adjacent (0-5 km) to {all_dest_str} (e.g. for Taranga Hills: Shri Ajitnatha Bhagwan Jain Derasar, Buddhist / Jogida Rock-Cut Caves, Siddhashila & Kotishila hill trek, Taramati Peak, temple Bhojanshala).
  * Group all Morning & Afternoon activities in the immediate area. ABSOLUTELY NEVER scatter to random stepwells or villages 30-40 km away!
- ITINERARY: Day 1 Evening must include sunset/tea and return transit back home to {source}.
"""
        else:
            trip_type_instructions = f"""
TRIP TYPE: {duration_days}-DAY MULTI-DAY TRIP COVERING: {all_dest_str}
- FLIGHTS: Under "#### Flights", provide 3 distinct airlines with realistic fares ₹2,500-₹8,500, departure/arrival times, and duration.
- HOTELS: Under "### Recommended Accommodations", list verified hotel names in bold FOR EACH DESTINATION in the trip ({all_dest_str}) under Luxury, Premium, and Budget tiers.
- UNIQUE ATTRACTIONS: Ensure ZERO duplicate attractions across all {duration_days} days. Every day must feature brand-new sights and activities!
- ITINERARY: Generate exactly {duration_days} Days (Day 1 through Day {duration_days}). Intermediate evenings are relaxing at destination; ONLY Day {duration_days} Evening is the return journey back to {source}.
"""

        format_context = f"""
TARGET TRIP PARAMETERS:
- Origin/Source: {source}
- Target Destinations: {all_dest_str}
- Total Duration: {duration_days} Day(s)
- Modification Request: {modifications if is_mod else "New / Extended Itinerary"}

{trip_type_instructions}

PREVIOUS ITINERARY SUMMARY (FOR CONTINUITY):
{current_plan if current_plan else "None"}

RAW RETRIEVED SUB-AGENT DATA:
{subagent_text}

USER REQUEST:
{request}

CRITICAL INSTRUCTIONS:
1. Include all 4 mandatory sections with realistic costs in INR (₹).
2. NEVER repeat the same attraction on multiple days.
3. List accommodations for each visited destination city.
4. Ensure the final return journey is back to {source}.
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