"""
Orchestrator Agent
===================
Owns the live TripState and routes work to every sub-agent. This is
the piece that makes the system "agentic" rather than a one-shot
generator: build() creates state once, but handle_disruption() and
ask() both operate on that *same* live state without the user having
to re-supply context.

Every step appends a line to state.agent_log so the dashboard can
show, in plain sight, which agent did what and why — the multi-agent
reasoning isn't hidden behind a single "Generate" button.
"""
import os
import uuid

from app.agents.budget import budget_agent
from app.agents.conversational import conversational_agent
from app.agents.disruption_monitor import disruption_monitor_agent
from app.agents.itinerary_builder import itinerary_builder_agent
from app.models import Budget, DisruptionType, TripRequest, TripState


class OrchestratorAgent:
    def __init__(self):
        self._store: dict[str, TripState] = {}

    def llm_active(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def build_trip(self, req: TripRequest) -> TripState:
        log = [
            f"🧭 Orchestrator: received request — {req.destination}, {req.days} day(s), "
            f"budget {req.budget_total}, crowd tolerance '{req.crowd_tolerance}'",
            f"🔍 Discovery Agent: scoring POIs for interests {req.interests or 'all categories'}",
        ]
        days = itinerary_builder_agent.build(
            destination=req.destination,
            days=req.days,
            interests=req.interests,
            crowd_tolerance=req.crowd_tolerance,
        )
        n_slots = sum(len(d.slots) for d in days)
        log.append(f"🗺️ Itinerary Builder: sequenced {n_slots} activities across {req.days} day(s)")

        spent = budget_agent.total_spent(days)
        log.append(f"💰 Budget Agent: estimated total spend {spent:.0f} / {req.budget_total:.0f}")

        trip_id = str(uuid.uuid4())[:8]
        state = TripState(
            trip_id=trip_id,
            destination=req.destination,
            crowd_tolerance=req.crowd_tolerance,
            budget=Budget(total=req.budget_total, spent=spent),
            days=days,
            agent_log=log,
        )
        self._store[trip_id] = state
        return state

    def get_trip(self, trip_id: str) -> TripState | None:
        return self._store.get(trip_id)

    def handle_disruption(self, trip_id: str, slot_id: str, disruption_type: DisruptionType) -> dict:
        state = self._store.get(trip_id)
        if state is None:
            return {"ok": False, "error": "trip not found"}

        state.agent_log.append(f"⚠️ Disruption Monitor: '{disruption_type}' event on slot {slot_id}")

        evaluation = disruption_monitor_agent.evaluate(state, slot_id, disruption_type)
        if not evaluation["triggered"]:
            state.agent_log.append(f"🧭 Orchestrator: no action taken — {evaluation['reason']}")
            return {"ok": False, "error": evaluation["reason"]}

        state.agent_log.append("🔍 Discovery Agent: consulting pre-ranked Shadow Itinerary for this slot")
        updated = disruption_monitor_agent.apply_swap(state, evaluation["slot"], disruption_type)
        updated.budget.spent = budget_agent.total_spent(updated.days)
        state.agent_log.append(f"🧭 Orchestrator: applied swap — {evaluation['slot'].swap_reason}")
        self._store[trip_id] = updated
        return {"ok": True, "state": updated, "swap_reason": evaluation["slot"].swap_reason}

    def ask(self, trip_id: str, question: str) -> str:
        state = self._store.get(trip_id)
        if state is None:
            return "I don't have a trip with that ID yet — build one first."
        state.agent_log.append(f"💬 Conversational Agent: answering — \"{question}\"")
        return conversational_agent.answer(state, question)


orchestrator_agent = OrchestratorAgent()
