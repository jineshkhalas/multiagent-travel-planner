import uvicorn

if __name__ == "__main__":
    print("Starting Flights A2A Agent on Port 8003...")
    uvicorn.run("agents.flights_agent.agent:a2a_app", host="127.0.0.1", port=8003, reload=True)