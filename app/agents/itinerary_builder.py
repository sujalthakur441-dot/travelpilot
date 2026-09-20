"""
Itinerary Builder Agent
=======================
Takes the POIs the Discovery Agent picked and sequences them into
day-by-day time slots. Keeps it simple for the MVP: 2 activities per
day, morning + afternoon, each carrying its own pre-computed Shadow
Itinerary (alternatives) from Discovery.
"""
from app.agents.discovery import discovery_agent
from app.models import ActivitySlot, Alternative, DayPlan

_TIME_SLOTS = ["09:00-11:00", "14:00-16:00", "17:00-19:00"]
_DEFAULT_CATEGORIES = ["tourist attractions", "restaurants", "markets", "landmarks"]


class ItineraryBuilderAgent:
    def build(self, destination: str, days: int, interests: list[str],
              crowd_tolerance: str) -> list[DayPlan]:
        categories = interests or discovery_agent.categories_for(destination) or _DEFAULT_CATEGORIES
        used_ids: set[str] = set()
        day_plans: list[DayPlan] = []

        cat_cycle = categories * ((days * len(_TIME_SLOTS)) // max(len(categories), 1) + 1)
        cat_index = 0

        for day_num in range(1, days + 1):
            slots: list[ActivitySlot] = []
            per_day = min(2, len(_TIME_SLOTS))
            for slot_i in range(per_day):
                category = cat_cycle[cat_index]
                cat_index += 1
                poi = discovery_agent.best_pick(destination, category, crowd_tolerance, used_ids)
                if poi is None:
                    continue
                used_ids.add(poi["id"])
                alts_raw = discovery_agent.shadow_alternatives(destination, poi, crowd_tolerance)
                alternatives = [Alternative(**a) for a in alts_raw]
                slots.append(ActivitySlot(
                    slot_id=f"d{day_num}-s{slot_i+1}",
                    time=_TIME_SLOTS[slot_i],
                    poi_id=poi["id"],
                    name=poi["name"],
                    category=poi["category"],
                    crowd_level=poi["crowd_level"],
                    cost=poi["cost"],
                    alternatives=alternatives,
                ))
            day_plans.append(DayPlan(date_label=f"Day {day_num}", slots=slots))

        return day_plans


itinerary_builder_agent = ItineraryBuilderAgent()
