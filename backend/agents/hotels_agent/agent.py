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

def fetch_api_hotels(city: str) -> list:
    """Queries Geoapify Places API for verified hotels and resorts."""
    geo_key = os.getenv("GEOAPIFY_API_KEY")
    if not geo_key or geo_key == "your_geoapify_key_here":
        return []

    try:
        # Step 1: Geocode city with smart variant resolution
        lon, lat = None, None
        queries = [city]
        if "hills" in city.lower():
            queries.append(city.replace("Hills", "Hill").replace("hills", "hill"))
        if " " in city:
            queries.append(city.split()[0])

        for q in queries:
            try:
                geo_url = f"https://api.geoapify.com/v1/geocode/search?text={q}&filter=countrycode:in&apiKey={geo_key}"
                geo_res = requests.get(geo_url, timeout=5).json()
                for f in geo_res.get("features", []):
                    formatted = f.get("properties", {}).get("formatted", "")
                    name = f.get("properties", {}).get("name", "")
                    first_word = q.lower().split()[0]
                    if first_word in formatted.lower() or first_word in name.lower() or len(geo_res.get("features", [])) == 1:
                        lon, lat = f["geometry"]["coordinates"]
                        break
                if lon is not None:
                    break
            except Exception:
                pass

        if lon is None:
            # Fallback to global search
            geo_url = f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={geo_key}"
            geo_res = requests.get(geo_url, timeout=5).json()
            if geo_res.get("features"):
                lon, lat = geo_res["features"][0]["geometry"]["coordinates"]

        if lon is None:
            return []

        # Step 2: Fetch hotels and accommodation places near coordinates
        places_url = (
            f"https://api.geoapify.com/v2/places?"
            f"categories=accommodation.hotel,accommodation.resort,accommodation.guest_house,accommodation.motel&"
            f"filter=circle:{lon},{lat},35000&limit=12&apiKey={geo_key}"
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
        print(f"[HotelsAgent] Geoapify API search error: {e}")
        return []

def fetch_web_tariffs(city: str) -> list:
    """Searches live web for real room prices and booking tariffs."""
    query = f"hotels and resorts in {city} luxury 5 star 3 star budget room tariff price per night INR"
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=5)
            results = [f"- {res['title']}: {res['content'][:200]}" for res in response.get('results', [])]
            if results:
                return results
        except Exception as e:
            print(f"[HotelsAgent] Tavily search error: {e}")

    try:
        results = DDGS().text(query, max_results=5)
        if results:
            return [f"- {res['title']}: {res['body'][:200]}" for res in results]
    except Exception as e:
        print(f"[HotelsAgent] DuckDuckGo search error: {e}")

    return []

def search_hotels(city: str) -> str:
    """Searches live web for luxury 5-star, 3-star comfort, and budget hotel options with nightly rates."""
    api_hotels = fetch_api_hotels(city)
    
    # 1. Luxury / 5-Star / 7-Star Search
    luxury_query = f"top 5 star luxury hotels resorts in {city} room price per night INR"
    luxury_results = search_query(luxury_query, max_res=2)

    # 2. 3-Star & 4-Star Comfort Search
    mid_query = f"best 3 star 4 star boutique hotels in {city} price per night INR"
    mid_results = search_query(mid_query, max_res=2)

    # 3. Budget / Cheap Stays Search
    budget_query = f"best budget cheap hotels homestays in {city} under 2000 INR price per night"
    budget_results = search_query(budget_query, max_res=2)

    output_sections = []

    if api_hotels:
        output_sections.append(
            f"### Verified Hotel Properties in {city}:\n" + "\n".join(api_hotels)
        )

    if luxury_results:
        output_sections.append(
            f"### Luxury 5-Star Stays ({city}):\n" + "\n".join(luxury_results)
        )

    if mid_results:
        output_sections.append(
            f"### 3-Star & 4-Star Stays ({city}):\n" + "\n".join(mid_results)
        )

    if budget_results:
        output_sections.append(
            f"### Budget & Cheap Stays ({city}):\n" + "\n".join(budget_results)
        )

    if output_sections:
        return "\n\n".join(output_sections)

    return f"Search hotels in {city}: Luxury 5-star, 3-star comfort, and budget stays available."

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

hotels_agent = LlmAgent(
    name="HotelsSpecialist",
    model=groq_model,
    instruction="""You are a hotel specialist. Provide real hotel recommendations grouped strictly into:
1. Luxury / 5-Star / 7-Star Stays (Top 2)
2. Premium / 3-Star & 4-Star Stays (Top 2)
3. Budget / Cheap Stays (Top 2)
Always specify real names, locations, and nightly tariffs in INR (₹).""",
    description="Provides tiered hotel recommendations and nightly rates in INR.",
    tools=[search_hotels]
)

a2a_app = to_a2a(hotels_agent)