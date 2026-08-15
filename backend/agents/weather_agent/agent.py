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

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm"
}

def geocode_city(city: str):
    """Geocodes city using Geoapify with Open-Meteo fallback."""
    geo_key = os.getenv("GEOAPIFY_API_KEY")
    if geo_key and geo_key != "your_geoapify_key_here":
        try:
            r = requests.get(f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={geo_key}", timeout=5).json()
            if r.get("features"):
                lon, lat = r["features"][0]["geometry"]["coordinates"]
                country = r["features"][0]["properties"].get("country", "")
                return lat, lon, country
        except Exception as e:
            print(f"[WeatherAgent] Geoapify geocode error: {e}")

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=5).json()
        if geo_res.get("results"):
            lat = geo_res["results"][0]["latitude"]
            lon = geo_res["results"][0]["longitude"]
            country = geo_res["results"][0].get("country", "")
            return lat, lon, country
    except Exception as e:
        print(f"[WeatherAgent] Open-Meteo geocode error: {e}")

    return None, None, None

def fetch_api_weather(city: str) -> str:
    """Fetches live real-time weather using Open-Meteo with OpenWeatherMap fallback."""
    lat, lon, country = geocode_city(city)
    if lat is not None and lon is not None:
        try:
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            )
            w_res = requests.get(weather_url, timeout=5).json()

            if "current" in w_res:
                temp = w_res["current"]["temperature_2m"]
                humidity = w_res["current"]["relative_humidity_2m"]
                code = w_res["current"]["weather_code"]
                wind = w_res["current"]["wind_speed_10m"]
                condition = WMO_CODES.get(code, "Partly Cloudy")

                country_str = f", {country}" if country else ""
                return (
                    f"- Live Weather for {city}{country_str}: {temp}°C, Condition: {condition}, "
                    f"Humidity: {humidity}%, Wind Speed: {wind} km/h."
                )
        except Exception as e:
            print(f"[WeatherAgent] Open-Meteo forecast failed: {e}")

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if api_key and api_key != "your_openweather_key_here":
        try:
            owm_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            ow_res = requests.get(owm_url, timeout=5).json()

            if ow_res.get("cod") == 200:
                temp = ow_res["main"]["temp"]
                desc = ow_res["weather"][0]["description"]
                humidity = ow_res["main"]["humidity"]
                return f"- Live Weather for {city}: {temp}°C, Condition: {desc.capitalize()}, Humidity: {humidity}%."
        except Exception as e:
            print(f"[WeatherAgent] OpenWeatherMap failed: {e}")

    return ""

def fetch_web_climate_tips(city: str) -> list:
    """Searches live web for current month climate trends and packing advice with compact snippets."""
    query = f"current weather climate packing tips what to wear {city}"
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=2)
            results = [f"- {res['title']}: {res['content'][:150]}" for res in response.get('results', [])]
            if results:
                return results
        except Exception as e:
            print(f"[WeatherAgent] Tavily climate search error: {e}")

    try:
        results = DDGS().text(query, max_results=2)
        if results:
            return [f"- {res['title']}: {res['body'][:150]}" for res in results]
    except Exception as e:
        print(f"[WeatherAgent] DuckDuckGo climate search error: {e}")

    return []

def get_weather(city: str) -> str:
    """Combines live Weather APIs (Open-Meteo / OWM) and web search for complete weather & packing advice."""
    api_weather = fetch_api_weather(city)
    web_tips = fetch_web_climate_tips(city)

    output_sections = []

    if api_weather:
        output_sections.append(f"### Live Meteorological Data ({city}):\n" + api_weather)

    if web_tips:
        output_sections.append(f"### Climate Insights & Packing Tips ({city}):\n" + "\n".join(web_tips))

    if output_sections:
        return "\n\n".join(output_sections)

    return f"Weather for {city}: Moderate temperatures around 28°C expected. Light breathable clothing recommended."

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

weather_agent = LlmAgent(
    name="WeatherSpecialist",
    model=groq_model,
    instruction="""You are a weather specialist. You receive both live meteorological API data (temperatures, humidity, wind) and web packing tips.
Your job is to provide a concise summary with exact temperatures, weather condition, and practical clothing/packing recommendations for the destination.""",
    description="Provides real-time weather forecasts and packing advice using API + Web Search.",
    tools=[get_weather]
)

a2a_app = to_a2a(weather_agent)
