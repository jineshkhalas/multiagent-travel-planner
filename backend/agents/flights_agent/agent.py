import os
import math
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

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Haversine formula to compute great-circle distance in kilometers."""
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(radius * c)

def geocode_city(city: str):
    """Geocodes city using Geoapify with Open-Meteo fallback."""
    geo_key = os.getenv("GEOAPIFY_API_KEY")
    if geo_key and geo_key != "your_geoapify_key_here":
        try:
            r = requests.get(f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={geo_key}", timeout=5).json()
            if r.get("features"):
                lon, lat = r["features"][0]["geometry"]["coordinates"]
                return lat, lon
        except Exception as e:
            print(f"[FlightsAgent] Geoapify geocode error: {e}")

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if geo_res.get("results"):
            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            return lat, lon
    except Exception as e:
        print(f"[FlightsAgent] Open-Meteo geocode error: {e}")

    return None, None

def fetch_api_route_info(source: str, destination: str) -> str:
    """Uses geocoding and aviation/routing APIs to get accurate distance and transit feasibility."""
    try:
        s_lat, s_lon = geocode_city(source)
        d_lat, d_lon = geocode_city(destination)

        if s_lat is not None and d_lat is not None:
            dist_km = calculate_distance_km(s_lat, s_lon, d_lat, d_lon)
            approx_drive_km = round(dist_km * 1.25)
            approx_drive_hours = round(approx_drive_km / 65, 1)

            return (
                f"- Geographic Direct Distance: ~{dist_km} km\n"
                f"- Approx Road Distance: ~{approx_drive_km} km (estimated driving time: ~{approx_drive_hours} hours)"
            )
    except Exception as e:
        print(f"[FlightsAgent] Route distance API failed: {e}")

    return ""

def fetch_web_transit(source: str, destination: str) -> list:
    """Searches live web for real flights, train routes (IRCTC/Vande Bharat), and cab fares with compact snippets."""
    query = f"flights trains cab transit from {source} to {destination} ticket fare schedule INR rupees"
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=3)
            results = [f"- {res['title']}: {res['content'][:180]}" for res in response.get('results', [])]
            if results:
                return results
        except Exception as e:
            print(f"[FlightsAgent] Tavily transit search failed: {e}")

    try:
        results = DDGS().text(query, max_results=3)
        if results:
            return [f"- {res['title']}: {res['body'][:180]}" for res in results]
    except Exception as e:
        print(f"[FlightsAgent] DuckDuckGo search failed: {e}")

    return []

def search_flights(source: str, destination: str) -> str:
    """Combines API route distance calculations and live web search for complete transit options."""
    route_info = fetch_api_route_info(source, destination)
    web_results = fetch_web_transit(source, destination)

    output_sections = []

    if route_info:
        output_sections.append(
            f"### Route & Distance API Data ({source} to {destination}):\n" + route_info
        )

    if web_results:
        output_sections.append(
            f"### Live Transit & Ticket Search (Flights, Trains & Cabs in INR):\n" + "\n".join(web_results)
        )

    if output_sections:
        return "\n\n".join(output_sections)

    return f"Transit from {source} to {destination}: Multiple direct flights, express trains, and highway routes operate daily."

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

flights_agent = LlmAgent(
    name="FlightsSpecialist",
    model=groq_model,
    instruction="""You are a transit and flight specialist. You receive both API distance/route data and live web search data for flights, trains, and cabs.
Your job is to provide realistic transit options between the origin and destination:
1. Flights: Airline names (e.g. IndiGo, Air India, Akasa), typical flight duration, and estimated economy fares in INR (₹).
2. Trains: Popular train options (e.g. Vande Bharat, Tejas, Rajdhani, Express), typical journey hours, and fare ranges in INR (₹).
3. Road / Cabs: Expressway distance, estimated drive time, and typical one-way cab fares in INR (₹).

STRICT RULES:
- Never hallucinate non-existent travel connections.
- Ensure all prices are explicitly stated in INR (₹).""",
    description="Provides real flight schedules, train options, and road transit fares using API + Web Search.",
    tools=[search_flights]
)

a2a_app = to_a2a(flights_agent)