import time

import requests

from config import FOOTBALL_API_KEY

BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY or ""}
TIMEOUT = 20

# Standings change at most a few times a day, and the free API tier allows only
# 10 requests/minute — cache them instead of asking once per agent per match.
STANDINGS_TTL = 60 * 60
_standings_cache = {}


def _get(path, params=None):
    try:
        response = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=TIMEOUT)
        if response.status_code == 429:
            print(f"football-data.org rate limit hit for {path}")
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"football-data.org request failed for {path}: {e}")
        return None
    except ValueError:
        print(f"football-data.org returned invalid JSON for {path}")
        return None


def fetch_matches(league_code, date_from, date_to):
    return _get(f"/competitions/{league_code}/matches", {"dateFrom": date_from, "dateTo": date_to})


def fetch_standings(league_code):
    return _get(f"/competitions/{league_code}/standings")


def get_standings_dict(league_code):
    cached = _standings_cache.get(league_code)
    if cached and time.time() - cached[0] < STANDINGS_TTL:
        return cached[1]

    data = fetch_standings(league_code)
    if not data or not data.get("standings"):
        # Keep serving stale data rather than nothing if the API fails.
        return cached[1] if cached else {}

    standings = {}
    for entry in data["standings"][0]["table"]:
        team = entry["team"]
        name = team.get("shortName") or team.get("name")
        standings[name] = {
            "position": entry["position"],
            "points": entry["points"],
            "played": entry["playedGames"],
            "won": entry["won"],
            "draw": entry["draw"],
            "lost": entry["lost"],
            "goal_difference": entry["goalDifference"],
        }

    _standings_cache[league_code] = (time.time(), standings)
    return standings
