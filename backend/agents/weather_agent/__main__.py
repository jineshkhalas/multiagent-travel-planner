import uvicorn

if __name__ == "__main__":
    print("Starting Weather A2A Agent on Port 8001...")
    uvicorn.run("agents.weather_agent.agent:a2a_app", host="127.0.0.1", port=8001, reload=True)