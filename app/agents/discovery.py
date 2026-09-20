"""
Discovery Agent
================
Ranks POIs by popularity / crowd / cost and pre-computes a "Shadow
Itinerary": the best offbeat + budget alternative for every POI,
scored *before* any disruption happens, so a replan never has to
search from scratch.

Score = alpha*Popularity - beta*Crowd + gamma*Proximity - delta*Cost

Place data: if GOOGLE_PLACES_API_KEY is set, POIs are fetched live
from Google Places Text Search and cached in-memory per
(destination, category). Without a key, it falls back to the local
mock dataset (app/data/pois.json) so the app still runs end-to-end
with zero API keys.

Google Places has no public "crowd level" field, so crowd_level here
is a heuristic derived from user_ratings_total (more reviews ~ more
foot traffic) — this is called out explicitly rather than presented
as a real live signal, matching the spec doc's honest-caveats section.
"""
import json
import os
from pathlib import Path

import requests

DATA_PATH = Path(__file__).parent.parent / "data" / "pois.json"
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

_CROWD_SCORE = {"Low": 0.1, "Medium": 0.5, "High": 1.0}

# weight presets per crowd_tolerance preference
_WEIGHTS = {
    "low":    {"alpha": 0.9, "beta": 1.6, "gamma": 0.3, "delta": 0.6},  # avoid crowds hard
    "medium": {"alpha": 1.0, "beta": 1.0, "gamma": 0.3, "delta": 0.5},
    "high":   {"alpha": 1.3, "beta": 0.4, "gamma": 0.3, "delta": 0.4},  # chase popularity
}


def _crowd_from_review_count(count: int) -> str:
    if count >= 3000:
        return "High"
    if count >= 500:
        return "Medium"
    return "Low"


class DiscoveryAgent:
    def __init__(self):
        with open(DATA_PATH) as f:
            self._mock_db: dict = json.load(f)
        self._live_cache: dict[tuple[str, str], list[dict]] = {}

    def _places_api_key(self) -> str | None:
        return os.environ.get("GOOGLE_PLACES_API_KEY")

    def categories_for(self, destination: str) -> list[str]:
        # Only meaningful for the mock dataset; live mode is driven by
        # whatever `interests` the user typed, so this is a UI hint only.
        return list(self._mock_db.get(destination, {}).keys())

    def pois_for_category(self, destination: str, category: str) -> list[dict]:
        if self._places_api_key():
            live = self._fetch_live(destination, category)
            if live:
                return live
            # live call failed or returned nothing — fall through to mock
        return self._mock_db.get(destination, {}).get(category, [])

    def _fetch_live(self, destination: str, category: str) -> list[dict]:
        cache_key = (destination.lower(), category.lower())
        if cache_key in self._live_cache:
            return self._live_cache[cache_key]

        try:
            resp = requests.get(
                PLACES_TEXT_SEARCH_URL,
                params={
                    "query": f"{category} in {destination}",
                    "key": self._places_api_key(),
                },
                timeout=6,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return []

        results = data.get("results", [])
        pois = []
        for r in results[:8]:
            review_count = r.get("user_ratings_total", 0)
            rating = r.get("rating", 3.5)
            price_level = r.get("price_level", 0)  # 0-4 scale from Places API
            loc = r.get("geometry", {}).get("location", {})
            pois.append({
                "id": r.get("place_id"),
                "name": r.get("name", "Unknown place"),
                "category": category,
                # normalize rating (0-5) + a review-volume boost, capped at 1.0
                "popularity": min((rating / 5.0) * 0.7 + min(review_count / 5000, 0.3), 1.0),
                "crowd_level": _crowd_from_review_count(review_count),
                "cost": price_level * 500,  # rough proxy, no real currency from Places
                "duration_min": 90,
                "opening_hours": "See listing",
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "tags": ["live-data"],
            })

        self._live_cache[cache_key] = pois
        return pois

    def score(self, poi: dict, crowd_tolerance: str = "medium", proximity: float = 0.5) -> float:
        w = _WEIGHTS.get(crowd_tolerance, _WEIGHTS["medium"])
        popularity = poi["popularity"]
        crowd = _CROWD_SCORE[poi["crowd_level"]]
        cost_norm = min(poi["cost"] / 1000, 1.0)  # normalize cost roughly
        return (
            w["alpha"] * popularity
            - w["beta"] * crowd
            + w["gamma"] * proximity
            - w["delta"] * cost_norm
        )

    def best_pick(self, destination: str, category: str, crowd_tolerance: str = "medium",
                   exclude_ids: set[str] | None = None) -> dict | None:
        exclude_ids = exclude_ids or set()
        candidates = [
            p for p in self.pois_for_category(destination, category)
            if p["id"] not in exclude_ids
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda p: self.score(p, crowd_tolerance))

    def shadow_alternatives(self, destination: str, poi: dict, crowd_tolerance: str = "medium",
                             limit: int = 2) -> list[dict]:
        """Pre-score every other POI in the same category as a standby swap."""
        candidates = [
            p for p in self.pois_for_category(destination, poi["category"])
            if p["id"] != poi["id"]
        ]
        ranked = sorted(candidates, key=lambda p: self.score(p, crowd_tolerance), reverse=True)
        out = []
        for alt in ranked[:limit]:
            out.append({
                "poi_id": alt["id"],
                "name": alt["name"],
                "crowd_level": alt["crowd_level"],
                "cost": alt["cost"],
                "reason": self._reason(poi, alt),
            })
        return out

    @staticmethod
    def _reason(original: dict, alt: dict) -> str:
        bits = []
        if _CROWD_SCORE[alt["crowd_level"]] < _CROWD_SCORE[original["crowd_level"]]:
            bits.append(f"less crowded ({alt['crowd_level']} vs {original['crowd_level']})")
        if alt["cost"] < original["cost"]:
            bits.append("cheaper")
        if "offbeat" in alt.get("tags", []):
            bits.append("offbeat pick")
        if not bits:
            bits.append("comparable alternative")
        return ", ".join(bits)


discovery_agent = DiscoveryAgent()
