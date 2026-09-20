"""
Conversational Agent
=====================
Answers natural-language questions against the live TripState.

Primary path: sends the live TripState as structured context to
Claude, so answers reason over the *actual* itinerary rather than
canned templates. Falls back to fast rule-based matching if no
ANTHROPIC_API_KEY is set, so the app still runs without one.
"""
from app.agents.budget import budget_agent
from app.llm import LLMUnavailable, complete
from app.models import TripState

_SYSTEM_PROMPT = """You are TravelPilot's conversational agent. You answer questions \
about a traveler's live itinerary using ONLY the trip data provided below. Be concise \
(2-3 sentences max), concrete, and reference actual place names, times, and numbers \
from the data. If asked a hypothetical ("what if X is cancelled"), use the listed \
alternatives to give a specific answer, not a generic one."""


class ConversationalAgent:
    def answer(self, state: TripState, question: str) -> str:
        try:
            return self._answer_with_llm(state, question)
        except LLMUnavailable:
            return self._answer_with_rules(state, question)

    def _answer_with_llm(self, state: TripState, question: str) -> str:
        context = self._state_to_context(state)
        user_message = f"Trip data:\n{context}\n\nQuestion: {question}"
        return complete(_SYSTEM_PROMPT, user_message)

    @staticmethod
    def _state_to_context(state: TripState) -> str:
        spent = budget_agent.total_spent(state.days)
        lines = [f"Destination: {state.destination}",
                 f"Budget: {spent:.0f} spent of {state.budget.total:.0f}"]
        for day in state.days:
            lines.append(f"\n{day.date_label}:")
            for s in day.slots:
                alt_names = ", ".join(a.name for a in s.alternatives) or "none"
                lines.append(
                    f"  - {s.time}: {s.name} [{s.category}] crowd={s.crowd_level} "
                    f"cost={s.cost} status={s.status} backups=[{alt_names}]"
                )
        if state.backup_log:
            lines.append("\nRecent swaps:")
            for b in state.backup_log[-3:]:
                lines.append(f"  - {b.original} -> {b.swapped_to} ({b.reason})")
        return "\n".join(lines)

    # ---- rule-based fallback (zero API keys needed) ----
    def _answer_with_rules(self, state: TripState, question: str) -> str:
        q = question.lower()

        if "budget" in q or "spent" in q or "cost" in q:
            spent = budget_agent.total_spent(state.days)
            remaining = state.budget.total - spent
            return f"You've spent ~{spent:.0f} of your {state.budget.total:.0f} budget — {remaining:.0f} remaining."

        if "tomorrow" in q or "day 2" in q:
            return self._describe_day(state, index=1)

        if "today" in q or "day 1" in q:
            return self._describe_day(state, index=0)

        if "crowd" in q:
            crowded = [
                f"{s.name} ({s.crowd_level})"
                for d in state.days for s in d.slots if s.crowd_level == "High"
            ]
            if crowded:
                return "Currently high-crowd: " + ", ".join(crowded)
            return "Nothing on your plan is flagged as High crowd right now."

        if "cancel" in q or "what if" in q:
            first_slot = next((s for d in state.days for s in d.slots), None)
            if first_slot and first_slot.alternatives:
                alt = first_slot.alternatives[0]
                return (f"If '{first_slot.name}' were cancelled, I'd swap it for "
                        f"'{alt.name}' — {alt.reason}.")
            return "I don't have a pre-ranked backup for that slot yet."

        return self._describe_day(state, index=0)

    @staticmethod
    def _describe_day(state: TripState, index: int) -> str:
        if index >= len(state.days):
            return "That day isn't in your itinerary."
        day = state.days[index]
        if not day.slots:
            return f"{day.date_label} is currently empty."
        parts = [f"{s.time}: {s.name} ({s.crowd_level} crowd)" for s in day.slots]
        return f"{day.date_label} — " + "; ".join(parts)


conversational_agent = ConversationalAgent()
