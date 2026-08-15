import os
import requests
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

def fetch_api_hotels(city: str) -> list:
    """Queries Geoapify Places API for verified hotels and resorts."""
    geo_key = os.getenv("GEOAPIFY_API_KEY")
    if not geo_key or geo_key == "your_geoapify_key_here":
        return []

    try:
        # Step 1: Geocode city
        geo_url = f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={geo_key}"
        geo_res = requests.get(geo_url, timeout=6).json()

        if not geo_res.get("features"):
            return []

        lon, lat = geo_res["features"][0]["geometry"]["coordinates"]

        # Step 2: Fetch hotels and accommodation places near coordinates
        places_url = (
            f"https://api.geoapify.com/v2/places?"
            f"categories=accommodation.hotel,accommodation.resort,accommodation.guest_house&"
            f"filter=circle:{lon},{lat},25000&limit=5&apiKey={geo_key}"
        )
        places_res = requests.get(places_url, timeout=6).json()

        verified_hotels = []
        for feature in places_res.get("features", []):
            prop = feature.get("properties", {})
            name = prop.get("name")
            address = prop.get("formatted") or prop.get("address_line1") or ""
            if name:
                verified_hotels.append(f"- {name} ({address})")

        return verified_hotels
    except Exception as e:
        print(f"[HotelsAgent] Geoapify API hotel search error: {e}")
        return []

def fetch_web_hotels(city: str) -> list:
    """Searches live web for real hotel tariffs and room rates per night with compact snippets."""
    query = f"top hotels resorts stay options in {city} room price per night INR rupees budget luxury"
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=3)
            results = [f"- {res['title']}: {res['content'][:180]}" for res in response.get('results', [])]
            if results:
                return results
        except Exception as e:
            print(f"[HotelsAgent] Tavily search error: {e}")

    try:
        results = DDGS().text(query, max_results=3)
        if results:
            return [f"- {res['title']}: {res['body'][:180]}" for res in results]
    except Exception as e:
        print(f"[HotelsAgent] DuckDuckGo search error: {e}")

    return []

def search_hotels(city: str) -> str:
    """Combines structured Places API hotel properties and live web search for best hotel options."""
    api_hotels = fetch_api_hotels(city)
    web_hotels = fetch_web_hotels(city)

    output_sections = []

    if api_hotels:
        output_sections.append(
            f"### Verified Hotel Properties (Places API Data for {city}):\n" + "\n".join(api_hotels)
        )

    if web_hotels:
        output_sections.append(
            f"### Live Web Search (Nightly Rates & Tariffs for {city}):\n" + "\n".join(web_hotels)
        )

    if output_sections:
        return "\n\n".join(output_sections)

    return f"Search hotels in {city}: Look for top-rated budget, mid-range, and luxury options on local booking platforms."

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

hotels_agent = LlmAgent(
    name="HotelsSpecialist",
    model=groq_model,
    instruction="""You are a hotel booking specialist. You receive both verified hotel property records from Places API and live web pricing data.
Your job is to recommend real, verified hotel and resort options categorized into budget, mid-range, and luxury with realistic nightly tariffs in INR (₹).

STRICT RULES:
1. ALWAYS extract real, named hotel properties from the provided data.
2. NEVER output generic placeholder names like 'Hotel 1', 'Hotel A', or 'Option 1'.
3. State prices explicitly in INR (₹) per night.""",
    description="Provides verified hotel options and pricing using API + Web Search.",
    tools=[search_hotels]
)

a2a_app = to_a2a(hotels_agent)