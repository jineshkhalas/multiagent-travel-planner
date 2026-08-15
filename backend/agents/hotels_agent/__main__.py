import uvicorn
if __name__ == "__main__":
    uvicorn.run("agents.hotels_agent.agent:a2a_app", host="127.0.0.1", port=8004, reload=True)