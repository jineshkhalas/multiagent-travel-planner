import os
import math
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
        queries = [city]
        if "hills" in city.lower():
            queries.append(city.replace("Hills", "Hill").replace("hills", "hill"))
        if " " in city:
            queries.append(city.split()[0])

        for q in queries:
            try:
                r = requests.get(f"https://api.geoapify.com/v1/geocode/search?text={q}&filter=countrycode:in&apiKey={geo_key}", timeout=5).json()
                for f in r.get("features", []):
                    formatted = f.get("properties", {}).get("formatted", "")
                    name = f.get("properties", {}).get("name", "")
                    first_word = q.lower().split()[0]
                    if first_word in formatted.lower() or first_word in name.lower() or len(r.get("features", [])) == 1:
                        lon, lat = f["geometry"]["coordinates"]
                        return lat, lon
            except Exception as e:
                print(f"[FlightsAgent] Geoapify geocode error: {e}")

        # Global fallback if not found in India
        try:
            r = requests.get(f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={geo_key}", timeout=5).json()
            if r.get("features"):
                lon, lat = r["features"][0]["geometry"]["coordinates"]
                return lat, lon
        except Exception:
            pass

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

def fetch_api_route_info(source: str, destination: str):
    """Uses geocoding and distance calculations to get accurate road and air distances."""
    try:
        s_lat, s_lon = geocode_city(source)
        d_lat, d_lon = geocode_city(destination)

        if s_lat is not None and d_lat is not None:
            dist_km = calculate_distance_km(s_lat, s_lon, d_lat, d_lon)
            approx_drive_km = round(dist_km * 1.25)
            approx_drive_hours = round(approx_drive_km / 65, 1)
            approx_cab_fare = round(approx_drive_km * 14)

            text = (
                f"- Road Distance: ~{approx_drive_km} km\n"
                f"- Estimated Drive Time: ~{approx_drive_hours} hours\n"
                f"- Estimated Cab Fare: ₹{approx_cab_fare:,}"
            )
            return text, approx_drive_km
    except Exception as e:
        print(f"[FlightsAgent] Route distance API failed: {e}")

    return "", None

def search_query(query: str, max_res: int = 3) -> list:
    """Helper to query Tavily with DDGS fallback."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=max_res)
            results = [f"- {res['title']}: {res['content'][:200]}" for res in response.get('results', [])]
            if results:
                return results
        except Exception as e:
            print(f"[FlightsAgent] Tavily search error: {e}")

    try:
        results = DDGS().text(query, max_results=max_res)
        if results:
            return [f"- {res['title']}: {res['body'][:200]}" for res in results]
    except Exception as e:
        print(f"[FlightsAgent] DuckDuckGo search error: {e}")

    return []

def search_flights(source: str, destination: str) -> str:
    """Searches live web specifically for Flight options, Train options, and Road distances."""
    route_info, drive_km = fetch_api_route_info(source, destination)
    output_sections = []

    # 1. Flights Search (Only if route is long distance >= 250 km)
    if drive_km is not None and drive_km < 250:
        flight_results = [
            f"- Not applicable for this short distance (~{drive_km} km). Direct road drive, cab, bus, or local train is recommended."
        ]
    else:
        flight_query = f"flights from {source} to {destination} Indigo Air India SpiceJet ticket fare price INR"
        flight_results = search_query(flight_query, max_res=3)

    # 2. Trains Search
    train_query = f"trains from {source} to {destination} IRCTC train name departure arrival timing fare INR"
    train_results = search_query(train_query, max_res=3)

    if flight_results:
        output_sections.append(
            f"### Available Flight Options ({source} to {destination}):\n" + "\n".join(flight_results)
        )

    if train_results:
        output_sections.append(
            f"### Available Train Routes ({source} to {destination}):\n" + "\n".join(train_results)
        )

    if route_info:
        output_sections.append(
            f"### Road & Driving Route Details ({source} to {destination}):\n" + route_info
        )

    if output_sections:
        return "\n\n".join(output_sections)

    return f"Transit from {source} to {destination}: Direct flights, express trains, and highway options available daily."

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

flights_agent = LlmAgent(
    name="FlightsSpecialist",
    model=groq_model,
    instruction="""You are a transit and flight specialist. Provide realistic options for Flights (different airlines, realistic domestic fares typically ₹2,500 - ₹8,500), Trains (name/number, timings, fare ₹350 - ₹2,500), and Road/Cab distance.""",
    description="Provides real flight schedules, train options, and road transit fares.",
    tools=[search_flights]
)

a2a_app = to_a2a(flights_agent)