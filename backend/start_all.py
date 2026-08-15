import subprocess
import sys
import time
import os

processes = []

def start_process(cmd, name):
    print(f"[*] Starting {name}...")
    p = subprocess.Popen([sys.executable] + cmd, cwd=os.path.dirname(__file__))
    processes.append((name, p))
    return p

def main():
    print("==================================================")
    print("🌍 Starting AI Travel Planner Multi-Agent System")
    print("==================================================")

    # Launch 4 A2A specialist micro-agents on internal localhost ports
    start_process(["-m", "uvicorn", "agents.weather_agent.agent:a2a_app", "--port", "8001", "--host", "127.0.0.1"], "Weather Agent (8001)")
    start_process(["-m", "uvicorn", "agents.attractions_agent.agent:a2a_app", "--port", "8002", "--host", "127.0.0.1"], "Attractions Agent (8002)")
    start_process(["-m", "uvicorn", "agents.flights_agent.agent:a2a_app", "--port", "8003", "--host", "127.0.0.1"], "Flights Agent (8003)")
    start_process(["-m", "uvicorn", "agents.hotels_agent.agent:a2a_app", "--port", "8004", "--host", "127.0.0.1"], "Hotels Agent (8004)")

    time.sleep(2)

    # Main API server port (default 8000, or 7860 on Hugging Face Spaces / cloud environments)
    main_port = str(os.getenv("PORT", "8000"))
    start_process(["-m", "uvicorn", "server:app", "--port", main_port, "--host", "0.0.0.0"], f"Main Backend Server ({main_port})")

    print(f"\n✅ All 4 Specialist Agents + FastAPI Server are running on port {main_port}!")
    print(f"📌 Public API listening on: http://0.0.0.0:{main_port}")
    print("Press Ctrl+C to terminate all services.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for name, p in processes:
            print(f"Terminating {name}...")
            p.terminate()
        print("All services stopped.")

if __name__ == "__main__":
    main()
