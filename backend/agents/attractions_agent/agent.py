import os
import requests
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
from duckduckgo_search import DDGS
from tavily import TavilyClient

from google.adk.agents import LlmAgent
from google.adk.models import LiteLlm
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Robustly load backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(env_path)
load_dotenv()

def fetch_api_places(destination: str) -> list:
    """Queries Geoapify Places API for verified attractions and landmarks."""
    geo_key = os.getenv("GEOAPIFY_API_KEY")
    if not geo_key or geo_key == "your_geoapify_key_here":
        return []

    try:
        # Step 1: Geocode destination
        geo_url = f"https://api.geoapify.com/v1/geocode/search?text={destination}&apiKey={geo_key}"
        geo_res = requests.get(geo_url, timeout=6).json()
        
        if not geo_res.get("features"):
            return []

        lon, lat = geo_res["features"][0]["geometry"]["coordinates"]

        # Step 2: Fetch tourism and attraction places near coordinates
        places_url = (
            f"https://api.geoapify.com/v2/places?"
            f"categories=tourism.sights,tourism.attraction,entertainment.culture,leisure.park&"
            f"filter=circle:{lon},{lat},25000&limit=5&apiKey={geo_key}"
        )
        places_res = requests.get(places_url, timeout=6).json()

        verified_places = []
        for feature in places_res.get("features", []):
            prop = feature.get("properties", {})
            name = prop.get("name")
            address = prop.get("formatted") or prop.get("address_line1") or ""
            if name:
                verified_places.append(f"- {name} ({address})")

        return verified_places
    except Exception as e:
        print(f"[AttractionsAgent] Geoapify API search error: {e}")
        return []

def fetch_web_attractions(destination: str) -> list:
    """Searches live web for ticket prices, timings, and travel costs with compact snippets."""
    query = f"top places to visit in {destination} entry ticket fee price distance transport food cost INR"
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=3)
            results = [f"- {res['title']}: {res['content'][:200]}" for res in response.get('results', [])]
            if results:
                return results
        except Exception as e:
            print(f"[AttractionsAgent] Tavily search error: {e}")

    try:
        results = DDGS().text(query, max_results=3)
        if results:
            return [f"- {res['title']}: {res['body'][:200]}" for res in results]
    except Exception as e:
        print(f"[AttractionsAgent] DuckDuckGo search error: {e}")

    return []

def get_attractions(destination: str) -> str:
    """Combines structured Places API data and live web search for best-in-class attraction recommendations."""
    api_places = fetch_api_places(destination)
    web_results = fetch_web_attractions(destination)

    output_sections = []

    if api_places:
        output_sections.append(
            f"### Verified Sights & Landmarks (Places API Data for {destination}):\n" + "\n".join(api_places)
        )

    if web_results:
        output_sections.append(
            f"### Live Web Search (Entry Fees, Timings & Food Costs for {destination}):\n" + "\n".join(web_results)
        )

    if output_sections:
        return "\n\n".join(output_sections)

    return f"Attractions data for {destination}: Search for top local sightseeing spots, cultural sites, and adventure activities."

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

attractions_agent = LlmAgent(
    name="AttractionsSpecialist",
    model=groq_model,
    instruction="""You are an attractions specialist. You receive both verified Places API landmarks and live web search data.
Your job is to synthesize these into top sightseeing recommendations with actual spot names, verified entry ticket prices in INR (₹), and realistic food/activity budgets.

STRICT RULES:
1. Use real, verified place names and exact ticket prices from the provided API & web data.
2. NEVER output generic disclaimer phrases like 'check official website' or 'information unavailable'.
3. Always state prices clearly in INR (₹).""",
    description="Provides verified attractions, ticket fees, and travel costs using API + Web Search.",
    tools=[get_attractions]
)

a2a_app = to_a2a(attractions_agent)