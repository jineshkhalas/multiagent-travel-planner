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

CRITICAL RULES:
1. SOURCE vs DESTINATIONS DISTINCTION:
   - "source": The starting/origin city where the traveler begins and returns to (e.g. "Ahmedabad" in "trip to Delhi from Ahmedabad").
   - "destinations": Array of ONLY the target destination cities the user wants to VISIT/TOUR (e.g. ["Delhi"], or ["Delhi", "Kullu Manali"]).
   - STRICT: NEVER put the source city inside the destinations array! The traveler does not tour their home city!
2. MULTI-DESTINATION EXTENSIONS:
   - If user previously planned a trip to Delhi from Ahmedabad, and now says "add 4 more days to visit Kullu Manali", source remains "Ahmedabad", and destinations become ["Delhi", "Kullu Manali"].
3. DURATION:
   - "duration_days": Total cumulative days for the entire trip (e.g. 1, 2, 6).
4. OUTPUT FORMAT: Return strictly a valid JSON object without markdown code blocks.
"""

FORMATTING_SYSTEM_PROMPT = """You are a master travel planner. Your job is to format and compile the retrieved specialist sub-agent data into a complete, clean, strictly structured, realistic, and non-repetitive travel itinerary.

MANDATORY STRUCTURAL RULES:
1. STRICT DESTINATION BOUNDARY: ONLY include activities, spots, and hotels located in the target destination cities.
   - ABSOLUTELY NEVER tour or visit attractions in the source city!
2. ALL 4 MAIN SECTIONS ARE STRICTLY MANDATORY (NEVER CUT OFF OR SKIP ANY SECTION):
   - Section 1: ### Flights & Transit Options
   - Section 2: ### Weather Conditions
   - Section 3: ### Recommended Accommodations
   - Section 4: ### Detailed Day-by-Day Itinerary
3. ZERO DUPLICATE ATTRACTIONS:
   - Every single day and time block MUST explore UNIQUE, NEVER-BEFORE-VISITED sights and activities.
   - ABSOLUTELY NEVER repeat the same attraction on multiple days!
4. STRICT ACCOMMODATION RULES:
   - For 1-DAY TRIPS (Same-Day Return): Output ONLY:
     "- **Same-Day Return**: Not applicable for a 1-day trip (return to [Source] the same evening/night). No overnight hotel stay is required."
     ABSOLUTELY NEVER output hotel tiers (Luxury / Premium / Budget) for 1-day trips!
   - For MULTI-DAY TRIPS (2+ Days): List verified hotels FOR EACH DESTINATION in the trip under Luxury (Top 2), Premium (Top 2), and Budget (Top 2).
     NEVER list hotels in the source/origin city!
5. FLIGHTS & TRANSIT:
   - If distance < 50 km (e.g. Ahmedabad to Gandhinagar, Mumbai to Thane): Direct Flights: Not applicable for this short distance (~X km). Local cab, auto, metro, or drive is recommended.
   - If the destination has a commercial airport or is an airport city (e.g. Mumbai, Delhi, Vadodara, Surat, Goa, Jaipur, Bangalore) OR if user requested flights: Provide flight options (IndiGo, Air India, SpiceJet with realistic fares ₹2,500-₹7,500).
   - If the destination is a small non-airport town or hill station (e.g. Taranga Hills, Dakor, Matheran): Write "- **Direct Flights**: Not applicable for this short-distance route (no commercial airport in [Destination]). Direct road drive (car/cab), bus, or local train is recommended."
6. COMPLETE FULL GENERATION:
   - Always generate the FULL itinerary with all days (Day 1 to Day N) and all time blocks (Morning, Afternoon, Evening). NEVER terminate early or omit any section.
7. ALL PRICES IN INR (₹):
   - Never use $ symbols. All costs must be in INR (₹).
8. CLEAN HEADERS:
   - Do NOT wrap markdown headers in bold (use `### Flights & Transit Options`, NOT `### **Flights & Transit Options**`).
   - Do NOT output raw emoji characters in headers or text.
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
                    temperature=0.3,
                    max_tokens=4096
                )
                content = resp.choices[0].message.content.strip()
                if content and len(content) > 30:
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
            for turn in history[-4:]:
                role = "User" if turn.get("role") == "user" else "Assistant"
                content = turn.get("content", "")
                if role == "Assistant" and len(content) > 200:
                    content = content[:200] + "... [previous plan]"
                history_formatted += f"{role}: {content}\n"

        context_prompt = f"""
CONVERSATION HISTORY:
{history_formatted if history_formatted else "No previous history."}

CURRENT SAVED ITINERARY SUMMARY:
{current_plan[:400] if current_plan else "No previous itinerary."}

NEW USER MESSAGE:
{request}

Extract and resolve persistent trip parameters:
- source (starting city where user lives)
- destinations (array of ONLY places to tour/visit, NEVER include source!)
- duration_days (total number of days)
- is_modification (boolean)
- modifications (summary)

Return JSON only.
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
            raw_src = parsed.get("source")
            if raw_src and isinstance(raw_src, str) and raw_src.strip().lower() not in ["none", "null", "unknown", ""]:
                source = raw_src.strip()

            raw_dest = parsed.get("destinations", [])
            if isinstance(raw_dest, list):
                destinations = [str(d).strip() for d in raw_dest if d and str(d).strip().lower() not in ["none", "null", "unknown", ""]]
            elif isinstance(raw_dest, str) and raw_dest.strip().lower() not in ["none", "null", "unknown", ""]:
                destinations = [str(d).strip() for d in raw_dest.split(",") if d and str(d).strip().lower() not in ["none", "null", "unknown", ""]]
            
            duration_days = parsed.get("duration_days") or 3
            is_mod = bool(parsed.get("is_modification", False))
            modifications = str(parsed.get("modifications") or "")
        except Exception as e:
            print(f"[System] Notice: JSON extraction used fallback.")

        import re
        lower_msg = request.lower() if request else ""
        day_match = re.search(r'(\d+)\s*(?:-| )?\s*days?', lower_msg)
        if day_match:
            duration_days = int(day_match.group(1))
        elif "one day" in lower_msg or "1-day" in lower_msg:
            duration_days = 1
        elif "picnic" in lower_msg:
            duration_days = 1

        if "add" in lower_msg and "more day" in lower_msg:
            add_match = re.search(r'add\s*(\d+)\s*more\s*days?', lower_msg)
            if add_match:
                added = int(add_match.group(1))
                if duration_days <= added:
                    duration_days = duration_days + added

        # Extract source and destination accurately from regex patterns like "to X from Y" or "from Y to X"
        to_match = re.search(r'to\s+([a-zA-Z\s]+?)(?:\s+from|\s+in|\s+for|$)', request, re.IGNORECASE)
        from_match = re.search(r'from\s+([a-zA-Z\s]+?)(?:\s+to|\s+in|\s+for|$)', request, re.IGNORECASE)

        if from_match:
            extracted_src = from_match.group(1).strip().title()
            if extracted_src:
                source = extracted_src
        elif not source or source == "Unknown":
            if "from ahmedabad" in lower_msg or ("ahmedabad" in lower_msg and "to" in lower_msg):
                source = "Ahmedabad"
            elif "from delhi" in lower_msg:
                source = "Delhi"
            elif "from mumbai" in lower_msg:
                source = "Mumbai"
            elif "from pune" in lower_msg:
                source = "Pune"

        source_lower = source.lower() if source else "unknown"

        if to_match:
            extracted_dest = to_match.group(1).strip().title()
            if extracted_dest and extracted_dest.lower() != source_lower:
                if not destinations or destinations == ["Unknown"] or not is_mod:
                    destinations = [extracted_dest]

        # Safety: Purge source city completely from destinations list
        if source and source != "Unknown":
            destinations = [d for d in destinations if d and isinstance(d, str) and d.lower() != source_lower]

        if not destinations or destinations == ["Unknown"]:
            if "delhi" in lower_msg and source_lower != "delhi":
                destinations = ["Delhi"]
            elif "vadodara" in lower_msg and source_lower != "vadodara":
                destinations = ["Vadodara"]
            elif "mumbai" in lower_msg and source_lower != "mumbai":
                destinations = ["Mumbai"]
            elif "jaipur" in lower_msg and source_lower != "jaipur":
                destinations = ["Jaipur"]
            elif "taranga" in lower_msg:
                destinations = ["Taranga Hills"]
            elif "dakor" in lower_msg:
                destinations = ["Dakor"]
            else:
                destinations = ["Delhi" if source_lower != "delhi" else "Mumbai"]

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
TRIP TYPE: 1-DAY SAME-DAY RETURN TRIP TO {all_dest_str} FROM {source}

OUTPUT TEMPLATE:

### Flights & Transit Options

#### Flights
- [If distance < 50 km (e.g. Ahmedabad to Gandhinagar): **Direct Flights**: Not applicable for this short distance (~X km). Local cab, auto, metro, or drive is recommended.
  Else if {all_dest_str} has a commercial airport or is an airport city (e.g. Mumbai, Delhi, Vadodara, Surat, Goa, Jaipur) OR if user requested flights: Provide morning departure and evening return flights:
  - **IndiGo**: Dep: 07:30 - Arr: 08:30 | Evening Return: 19:30 - 20:30 | Price: ₹3,200 | Duration: 1h 0m
  - **Air India**: Dep: 09:00 - Arr: 10:00 | Evening Return: 20:00 - 21:00 | Price: ₹3,800 | Duration: 1h 0m
  Else if non-airport town (e.g. Taranga Hills, Dakor, Matheran):
  - **Direct Flights**: Not applicable for this short-distance route (no commercial airport in {all_dest_str}). Direct road drive (car/cab), bus, or local train is recommended.]

#### Trains
- **[Train 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **[Train 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

#### Road & Local Transit
- **Car / Cab**: ~[X] km | ~[Y] hours drive | Approx. ₹[Fare]
- **Bus / State Transport**: AC Sleeper / Volvo | ~[Y] hours | Approx. ₹[Fare]
- **Local City Transit**: Autos, Metro, and Taxis available for ₹10 - ₹150 per ride.

### Weather Conditions

#### Live Weather & Packing Tips
- **Temperature & Condition**: [Current Temp]°C, [Condition]
- **Humidity & Wind**: [Humidity]%, [Wind Speed] km/h
- **Packing Advice**: [Practical clothing and travel advice]

### Recommended Accommodations

- **Same-Day Return**: Not applicable for a 1-day trip (return to {source} the same evening/night). No overnight hotel stay is required.
(STRICT: Do NOT output any Luxury / Premium / Budget hotel lists on a 1-day trip!)

### Detailed Day-by-Day Itinerary

#### Day 1: {all_dest_str} Tour
- **Morning**: [Activity 1 in {all_dest_str}] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2 in {all_dest_str}]
- **Afternoon**: [Activity 1 in {all_dest_str}] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2 in {all_dest_str}]
- **Evening**: [Activity 1 in {all_dest_str}] • Dinner (₹[Amount]) • Return journey back to {source} [by flight or road/train]
"""
        else:
            trip_type_instructions = f"""
TRIP TYPE: {duration_days}-DAY MULTI-DAY TRIP TO {all_dest_str} FROM {source}
- YOU MUST PLAN ALL {duration_days} DAYS ENTIRELY TO TOUR {all_dest_str}. NEVER tour {source}!
- If multi-destination (e.g. Delhi and Kullu Manali), divide the days across the destinations in logical sequence.

OUTPUT TEMPLATE:

### Flights & Transit Options

#### Flights
- **[Airline 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare between 2,500 and 8,500] | Duration: [X]h [Y]m
- **[Airline 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare between 2,500 and 8,500] | Duration: [X]h [Y]m
- **[Airline 3]**: Dep: [Time] - Arr: [Time] | Price: ₹[Fare between 2,500 and 8,500] | Duration: [X]h [Y]m

#### Trains
- **[Train 1]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m
- **[Train 2]**: Dep: [Time] - Arr: [Time] | Price: ₹[Amount] | Duration: [X]h [Y]m

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

#### Luxury / 5-Star Stays (Top 2 per destination in {all_dest_str})
- **[Real Hotel 1]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night
- **[Real Hotel 2]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night

#### Premium / 3-Star & 4-Star Stays (Top 2 per destination in {all_dest_str})
- **[Real Hotel 1]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night
- **[Real Hotel 2]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night

#### Budget & Cheap Stays (Top 2 per destination in {all_dest_str})
- **[Real Hotel 1]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night
- **[Real Hotel 2]**: [City - Location / Highlights] | Approx. ₹[Tariff] / night

### Detailed Day-by-Day Itinerary

For each Day (Day 1 to Day {duration_days}):
#### Day X: [Destination City Theme]
- **Morning**: [Activity 1 in Destination] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
- **Afternoon**: [Activity 1 in Destination] (Distance: [X] km | Taxi: ₹[Amount] | Entry: ₹[Amount] | Food: ₹[Amount]) • [Activity 2]
- **Evening**: [Activity 1 in Destination] (Taxi: ₹[Amount] | Entry: ₹[Amount]) • Dinner at local restaurant (₹[Amount]) [Only on Day {duration_days}: • Return journey back to {source}]
"""

        format_context = f"""
TARGET TRIP PARAMETERS:
- Origin/Source: {source} (STRICT: Starting point only, DO NOT plan tours in {source}!)
- Target Destinations: {all_dest_str} (Plan all sightseeing exclusively in {all_dest_str}!)
- Total Duration: {duration_days} Day(s)
- Modification Request: {modifications if is_mod else "New / Extended Itinerary"}

{trip_type_instructions}

PREVIOUS ITINERARY SUMMARY (FOR CONTINUITY):
{current_plan if current_plan else "None"}

RAW RETRIEVED SUB-AGENT DATA:
{subagent_text}

USER REQUEST:
{request}

CRITICAL RULES:
1. All itinerary days must be in {all_dest_str}. NEVER include {source} in sightseeing!
2. All 4 sections must be fully generated without truncating.
3. Accommodations must only be for {all_dest_str}, NEVER for {source}.
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