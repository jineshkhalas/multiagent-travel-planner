from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.models import LiteLlm

load_dotenv()

groq_model = LiteLlm(model="groq/llama-3.1-8b-instant")

weather_sub = RemoteA2aAgent(name="WeatherRemote", url="http://127.0.0.1:8001")
attractions_sub = RemoteA2aAgent(name="AttractionsRemote", url="http://127.0.0.1:8002")
flights_sub = RemoteA2aAgent(name="FlightsRemote", url="http://127.0.0.1:8003")
hotels_sub = RemoteA2aAgent(name="HotelsRemote", url="http://127.0.0.1:8004")

root_agent = LlmAgent(
    name="TravelPlannerRoot",
    model=groq_model,
    instruction="""You are a master travel planner coordinator. 
    You have access to specialist sub-agents for Weather, Attractions, Flights, and Hotels.
    When a user asks to plan a trip, figure out which sub-agents you need to query, 
    gather their responses, and compile them into a single beautifully formatted travel itinerary.
    Do not make up flight or hotel data; rely on your sub-agents.""",
    description="Coordinates travel planning by delegating to specialist sub-agents.",
    agents=[weather_sub, attractions_sub, flights_sub, hotels_sub]
)