import os
import sys
import uvicorn

# Ensure backend dir is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def main():
    port = int(os.getenv("PORT", 8000))
    print("==================================================")
    print(f"[*] Starting AI Travel Planner API on port {port}")
    print("==================================================")
    uvicorn.run("server:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
