from dotenv import load_dotenv
load_dotenv()

import base64
import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.agents.monitor_loop import MonitorLoop
from app.agents.orchestrator import orchestrator_agent
from app.models import AskRequest, DisruptionRequest, TripRequest, TripState

app = FastAPI(title="TravelPilot", version="0.1.0")
monitor_loop = MonitorLoop(orchestrator_agent)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    Gates the whole app (dashboard + API) behind a single shared
    username/password, shown as the browser's native login prompt.

    Only active when DASHBOARD_USERNAME and DASHBOARD_PASSWORD are
    both set — local development stays open by default. This is
    meant to give judges one link + one login they can reuse across
    multiple test sessions, not per-user accounts.
    """
    async def dispatch(self, request: Request, call_next):
        expected_user = os.environ.get("DASHBOARD_USERNAME")
        expected_pass = os.environ.get("DASHBOARD_PASSWORD")
        if not expected_user or not expected_pass:
            return await call_next(request)  # auth disabled — no creds configured

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                given_user, given_pass = decoded.split(":", 1)
            except Exception:
                given_user, given_pass = "", ""
            if (secrets.compare_digest(given_user, expected_user)
                    and secrets.compare_digest(given_pass, expected_pass)):
                return await call_next(request)

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="TravelPilot"'},
            content="Authentication required.",
        )


app.add_middleware(BasicAuthMiddleware)


@app.get("/api/status")
def status():
    return {
        "llm_active": orchestrator_agent.llm_active(),
        "places_live": bool(os.environ.get("GOOGLE_PLACES_API_KEY")),
    }


@app.post("/api/trip", response_model=TripState)
def create_trip(req: TripRequest):
    """Build a new itinerary from traveler constraints."""
    return orchestrator_agent.build_trip(req)


@app.post("/api/trip/{trip_id}/autopilot/start")
def start_autopilot(trip_id: str):
    if orchestrator_agent.get_trip(trip_id) is None:
        raise HTTPException(404, "trip not found")
    started = monitor_loop.start(trip_id)
    return {"started": started, "running": monitor_loop.is_running(trip_id)}


@app.post("/api/trip/{trip_id}/autopilot/stop")
def stop_autopilot(trip_id: str):
    stopped = monitor_loop.stop(trip_id)
    return {"stopped": stopped, "running": monitor_loop.is_running(trip_id)}


@app.get("/api/trip/{trip_id}/autopilot/status")
def autopilot_status(trip_id: str):
    return {"running": monitor_loop.is_running(trip_id)}


@app.get("/api/trip/{trip_id}", response_model=TripState)
def get_trip(trip_id: str):
    state = orchestrator_agent.get_trip(trip_id)
    if state is None:
        raise HTTPException(404, "trip not found")
    return state


@app.post("/api/trip/{trip_id}/disruption")
def trigger_disruption(trip_id: str, req: DisruptionRequest):
    """
    Simulates the Disruption Monitor firing: swaps the given slot for
    its top pre-ranked Shadow Itinerary alternative and returns the
    updated live state, with the reason the swap happened.
    """
    result = orchestrator_agent.handle_disruption(trip_id, req.slot_id, req.disruption_type)
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return {"swap_reason": result["swap_reason"], "state": result["state"]}


@app.post("/api/trip/{trip_id}/ask")
def ask(trip_id: str, req: AskRequest):
    answer = orchestrator_agent.ask(trip_id, req.question)
    return {"answer": answer}


# Serve the dashboard at http://localhost:8000/
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
