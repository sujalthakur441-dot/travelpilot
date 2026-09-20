"""
Budget Agent
============
Tracks running spend across the itinerary and flags overruns. In the
MVP this is a pure function over the current state; in a fuller build
it would also propose cheaper swaps by calling the Discovery Agent
when the ceiling is hit.
"""
from app.models import DayPlan


class BudgetAgent:
    def total_spent(self, days: list[DayPlan]) -> float:
        return sum(slot.cost for day in days for slot in day.slots)

    def is_over_budget(self, days: list[DayPlan], budget_total: float) -> bool:
        return self.total_spent(days) > budget_total

    def remaining(self, days: list[DayPlan], budget_total: float) -> float:
        return budget_total - self.total_spent(days)


budget_agent = BudgetAgent()
