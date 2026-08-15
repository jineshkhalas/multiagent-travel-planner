import uvicorn

if __name__ == "__main__":
    print("Starting Attractions A2A Agent on Port 8002...")
    uvicorn.run("agents.attractions_agent.agent:a2a_app", host="127.0.0.1", port=8002, reload=True)