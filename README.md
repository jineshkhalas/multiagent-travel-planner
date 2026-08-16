# Multi-Agent AI Travel Planner (A2A Architecture)

> **Live Demo**: [https://multiagent-travel-planner.vercel.app](https://multiagent-travel-planner.vercel.app)

An end-to-end full-stack AI travel planning platform built with a multi-agent system. Instead of relying on a single monolithic LLM prompt that hallucinates routes, hotel names, or prices, this project coordinates **Specialist AI Agents** using Google's **Agent Development Kit (ADK)** and the **Agent-to-Agent (A2A)** architecture.

To produce accurate, practical, and grounded itineraries, each agent combines **Structured Geographical & Meteorological APIs** (for verified locations, exact coordinates, and property names) with **Live Web Search** (for real flight schedules, IRCTC train tickets, entry fees, and hotel room tariffs in INR).

---

## Key Features

- **Conversational Memory & Dynamic Sequence Resolution**:
  - Distinguishes the traveler's origin/source city (e.g. *Ahmedabad*) from destination cities (e.g. *Delhi, Kullu Manali*).
  - Keeps all sightseeing and activities strictly inside the destination cities, never placing home-city tours in the itinerary.
  - Multi-destination trip extensions preserve origin context and structure multi-city legs in logical chronological order.
- **Airport-Aware Flight & Transit Logic**:
  - **1-Day Trips to Airport Cities**: Automatically provisions morning outbound departures and evening return flights with verified round-trip fares.
  - **Short Commutes (< 50 km)**: Identifies adjacent cities (e.g. *Ahmedabad &rarr; Gandhinagar*) and recommends expressway drives, cabs, or metro lines instead of flights.
  - **Small Towns / Hill Stations**: Detects destinations without commercial airports (e.g. *Taranga Hills, Dakor, Matheran*) and suggests direct road cabs or express trains while keeping 1-day sightseeing within a tight 15–20 km radius.
- **Zero-Duplicate Sightseeing Engine**:
  - Strictly prevents repetitive attractions across multi-day itineraries. Every time block explores distinct cultural, historical, nature, or culinary landmarks.
- **Tiered Real Accommodations**:
  - For multi-day trips, provides verified hotels per visited destination categorized into **Luxury / 5-Star**, **Premium / 3-Star & 4-Star**, and **Budget / Cheap Stays** with real tariffs in INR (₹).
  - For 1-day same-day return trips, automatically outputs a clean single-line same-day return note with zero unnecessary hotel listings.
- **Multi-Model Fallback & High-Throughput Pipeline**:
  - Powered by Groq's high-speed inference pipeline with automated failover (`gpt-oss-20b` &rarr; `gpt-oss-safeguard-20b` &rarr; `gpt-oss-120b` &rarr; `llama-3.3-70b-versatile`) to eliminate rate-limit blackouts and guarantee complete responses.
- **Modern User Experience & Dashboard**:
  - Dual theme with instant Light / Dark mode toggle.
  - Newest-first dashboard cards with real-time Firebase Firestore synchronization.
  - Google Authentication via Firebase Auth.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Client ["1. Frontend & Client Layer"]
        User(["Traveler"]) <--> UI["React 19 UI (Vite + CSS) / CLI"]
    end

    subgraph Master ["2. Master Orchestrator (FastAPI)"]
        UI <-->|POST /api/plan| API["FastAPI Server (Port 8000 / Cloud PORT)"]
        API --> ContextAgent["Context & Memory Resolver\n(Resolves Source, Destinations, Days, History)"]
        ContextAgent --> Dispatcher["Parallel Domain Dispatcher"]
        Aggregator["Specialist Data Aggregator"] --> FormattingAgent["Formatting & Synthesis Engine\n(Generates Structured Itinerary in INR)"]
        FormattingAgent --> API
    end

    subgraph Specialists ["3. Specialist Data & Tool Services"]
        Dispatcher -.-> W["Weather Specialist\n(Geoapify + Open-Meteo + Packing Tips)"]
        Dispatcher -.-> A["Attractions Specialist\n(Geoapify Places API + Tavily Search)"]
        Dispatcher -.-> F["Flights & Transit Specialist\n(Haversine Distance + Flights/IRCTC Fares)"]
        Dispatcher -.-> H["Hotels Specialist\n(Accommodation API + Tiered Tariffs)"]

        W -.-> Aggregator
        A -.-> Aggregator
        F -.-> Aggregator
        H -.-> Aggregator
    end
```

---

## Architecture Breakdown

| Layer | Component | Implementation | Description |
| :--- | :--- | :--- | :--- |
| **Frontend** | React 19 + Vite | `frontend/` | Fast responsive UI with Firebase Google Auth, Cloud Firestore sync, Lucide icons, and Dark Mode. |
| **Orchestrator** | FastAPI Backend | `backend/server.py` | Handles conversation memory, parallel agent dispatch, and final itinerary synthesis. |
| **Specialist 1: Weather** | Meteorology Agent | `backend/agents/weather_agent/` | Geoapify geocoding + Open-Meteo API + Tourist packing insights. |
| **Specialist 2: Attractions** | Sightseeing Agent | `backend/agents/attractions_agent/` | Geoapify Places API for verified landmarks + Web search for entry fees and food budgets. |
| **Specialist 3: Flights/Transit** | Transit Agent | `backend/agents/flights_agent/` | Great-circle distance calculations + Web search for flights, IRCTC trains, and road cab routes. |
| **Specialist 4: Hotels** | Accommodation Agent | `backend/agents/hotels_agent/` | Geoapify Accommodation API + Web search for Luxury 5-Star, 3/4-Star, and Budget stays. |

---

## Tech Stack

### Backend
- **FastAPI & Uvicorn**: High-performance asynchronous web framework and ASGI server.
- **Google ADK & LiteLLM**: Agent-to-Agent (A2A) multi-agent protocol and LLM gateway.
- **Groq API**: High-speed inference powering `gpt-oss-20b`, `gpt-oss-safeguard-20b`, `gpt-oss-120b`, and `llama-3.3-70b-versatile`.
- **Geoapify API**: Geocoding, reverse geocoding, and Places API for verified points of interest and hotels.
- **Open-Meteo & OpenWeatherMap**: Real-time meteorological data and weather forecasting.
- **Tavily AI & DuckDuckGo Search**: Real-time live web search for dynamic ticket fares, flight timings, and tariffs.

### Frontend
- **React 19 & Vite**: Ultra-fast single-page application framework.
- **Firebase Authentication & Cloud Firestore**: Secure user login and real-time trip persistence.
- **React-Markdown**: Rich markdown rendering for structured travel plans.
- **Tailwind CSS & Lucide React**: Clean vector iconography and modern responsive styling.
- **Custom Typography**: Google Fonts McLaren (Headings) and Plus Jakarta Sans (Body).

---

## Local Setup & Installation

### 1. Prerequisites
- **Python 3.10+** (or Anaconda / Miniconda)
- **Node.js 18+** and npm

### 2. Clone the Repository
```bash
git clone https://github.com/jineshkhalas/multiagent-travel-planner.git
cd multiagent-travel-planner
```

### 3. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

Fill in your API keys in `backend/.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
GEOAPIFY_API_KEY=your_geoapify_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
OPENWEATHER_API_KEY=your_openweather_key_here
PORT=8000
```

Start the backend API server:
```bash
python start_all.py
```
Backend will run at `http://localhost:8000`.

### 4. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

Configure your Firebase credentials and backend URL in `frontend/.env`:
```env
VITE_BACKEND_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_FIREBASE_MEASUREMENT_ID=your_measurement_id
```

Start the frontend development server:
```bash
npm run dev
```
Frontend will be accessible at `http://localhost:5173`.

---

## Production Deployment

### Backend on Render.com
1. Create a new **Web Service** on [Render](https://render.com) connected to your GitHub repository.
2. Set **Root Directory** to `backend`.
3. Set **Runtime** to `Python 3`.
4. Set **Build Command**: `pip install -r requirements.txt`.
5. Set **Start Command**: `python start_all.py`.
6. Add your Environment Variables in the Render dashboard (`GROQ_API_KEY`, `GEOAPIFY_API_KEY`, `TAVILY_API_KEY`, `PORT=8000`).

### Frontend on Vercel
1. Import your repository into [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set **Framework Preset** to `Vite`.
4. Configure Environment Variables in Vercel settings (`VITE_BACKEND_URL` pointing to your Render service URL, plus Firebase keys).
5. Deploy.

---

## License

This project is licensed under the MIT License.
