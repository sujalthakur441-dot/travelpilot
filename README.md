# TravelPilot — MVP

Agentic AI trip planner: builds a day-by-day itinerary, then
autonomously replans it when a disruption hits — using a pre-scored
**Shadow Itinerary** of alternatives instead of searching from scratch.

## Run it

```bash
cd travelpilot
python3 -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt
cp .env.example .env      # optional — add your ANTHROPIC_API_KEY to enable real LLM reasoning
uvicorn app.main:app --reload
```

Then open **http://localhost:8000** — the dashboard is served
straight from the FastAPI app, no separate frontend build needed.

## Autonomous Monitoring (Autopilot)

Click **Start Autopilot** on the dashboard and the Disruption Monitor
takes over: every ~8 seconds it has a chance to fire a real
disruption on a live slot and the Orchestrator resolves it through
the normal pipeline — no manual "Trigger Disruption" click needed.
This is what makes the "no re-prompt needed" claim literally true on
stage rather than staged. It stops automatically after a few swaps
or when you click **Stop Autopilot**.

## AI Integration

Set `ANTHROPIC_API_KEY` in `.env` and two agents switch from
rule-based to real Claude reasoning automatically — no code changes
needed, and the app still runs fine without a key:

- **Conversational Agent** — sends the live TripState as structured
  context to Claude and answers questions by reasoning over the
  actual itinerary, not canned templates.
- **Disruption Monitor** — asks Claude to write the natural-language
  explanation for each swap, grounded in the real before/after data
  (it can't invent a place that isn't the actual alternative).

Set `GOOGLE_PLACES_API_KEY` and the Discovery Agent switches from the
local mock dataset to live Google Places Text Search for any
destination, not just Goa. Crowd level in live mode is a heuristic
from review volume (Places has no public crowd API) — this is called
out honestly rather than presented as a real live signal.

The dashboard's top-right badges show live whether Claude reasoning
and live Places data are active — useful to show judges directly.

## Deployment (live link + credentials for judges)

See `DEPLOY.md` for full steps. Short version: set
`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` in your environment to
gate the whole app behind one shared login (browser's native
prompt), then deploy via `render.yaml` (Render), the included
`Dockerfile` (Railway/Fly.io), or `Procfile` (Heroku-style). Hand
judges the live URL plus that username/password.

## Demo flow (matches the pitch)

1. Fill in destination / days / budget / interests / crowd tolerance → **Build Itinerary**.
2. Watch the day-by-day plan render, each activity already carrying
   pre-ranked alternatives under the hood. The **Agent Activity Log**
   panel shows each agent's step in real time.
3. Pick a slot in **"Simulate a disruption"**, choose a disruption
   type (e.g. crowd spike), and fire it.
4. The dashboard updates *without a new prompt* — the swapped
   activity is highlighted green with the reason shown, exactly the
   "no re-prompt needed" moment from the pitch.
5. Ask a question in the chat box ("what should I do tomorrow?",
   "what's over budget?", "what if this is cancelled?") — answered
   against the live state.

## Where each agent lives

| Agent | File |
|---|---|
| Orchestrator | `app/agents/orchestrator.py` |
| Discovery (scoring + Shadow Itinerary) | `app/agents/discovery.py` |
| Itinerary Builder | `app/agents/itinerary_builder.py` |
| Budget | `app/agents/budget.py` |
| Disruption Monitor | `app/agents/disruption_monitor.py` |
| Conversational | `app/agents/conversational.py` |
| LLM wrapper | `app/llm.py` |

## What's mocked vs. real right now

- **POI data** falls back to `app/data/pois.json` (Goa only, ~10
  places) unless `GOOGLE_PLACES_API_KEY` is set, in which case it's
  live for any destination — see "AI Integration" above.
- **Crowd level** is a static field per mock POI, or a review-volume
  heuristic in live Places mode — standing in for a real
  Popular-Times-style signal (no official public API exists for
  that).
- **LLM reasoning** is real once `ANTHROPIC_API_KEY` is set.
- **Disruption events** happen autonomously once Autopilot is
  started — see "Autonomous Monitoring" above — or can still be
  triggered manually for a controlled demo moment.

## Fastest next steps

1. Persist state to a real DB (currently in-memory, resets on
   restart) if you need trips to survive a server reload.
2. Add opening-hours-aware scheduling (currently fixed time slots).
3. Real travel-time between slots via Google Directions API instead
   of assumed durations.
