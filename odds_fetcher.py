from datetime import datetime, timedelta, timezone

import requests
from thefuzz import process

from config import LEAGUES, ODDS_API_KEY
from database import get_bettable_matches, update_match_odds

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
TIMEOUT = 20
MATCH_THRESHOLD = 60
LOOKAHEAD_DAYS = 3


def find_matching_team(db_name, api_teams, threshold=MATCH_THRESHOLD):
    result = process.extractOne(db_name, api_teams)
    if result and result[1] >= threshold:
        return result[0]
    return None


def fetch_odds(league_code):
    league = LEAGUES.get(league_code)
    if not league or not ODDS_API_KEY:
        return []

    try:
        response = requests.get(
            f"{ODDS_API_BASE}/sports/{league['odds_key']}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        print(f"Error fetching odds for {league_code}: {e}")
        return []

    if response.status_code != 200:
        print(f"Error fetching odds for {league_code}: {response.status_code}")
        return []

    try:
        return response.json()
    except ValueError:
        return []


def get_average_odds(bookmakers, home_team, away_team):
    """Average h2h odds across all bookmakers."""
    home_odds, draw_odds, away_odds = [], [], []

    for bookmaker in bookmakers:
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                if outcome["name"] == home_team:
                    home_odds.append(outcome["price"])
                elif outcome["name"] == away_team:
                    away_odds.append(outcome["price"])
                elif outcome["name"] == "Draw":
                    draw_odds.append(outcome["price"])

    def avg(values):
        return round(sum(values) / len(values), 2) if values else None

    return avg(home_odds), avg(draw_odds), avg(away_odds)


def update_odds_for_league(league_code):
    odds_data = fetch_odds(league_code)
    if not odds_data:
        print(f"{league_code}: no odds data")
        return

    date_to = (datetime.now(timezone.utc) + timedelta(days=LOOKAHEAD_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db_matches = [m for m in get_bettable_matches(date_to) if m["league"] == league_code]

    updates = []
    used = set()
    for api_match in odds_data:
        api_home, api_away = api_match["home_team"], api_match["away_team"]
        odds_home, odds_draw, odds_away = get_average_odds(api_match.get("bookmakers", []), api_home, api_away)
        if not (odds_home and odds_draw and odds_away):
            continue

        for db_match in db_matches:
            if db_match["match_id"] in used:
                continue
            home_match = find_matching_team(db_match["home_team"], [api_home, api_away])
            away_match = find_matching_team(db_match["away_team"], [api_home, api_away])
            if home_match == api_home and away_match == api_away:
                updates.append((odds_home, odds_draw, odds_away, db_match["match_id"]))
                used.add(db_match["match_id"])
                break

    update_match_odds(updates)
    print(f"{league_code}: updated odds for {len(updates)} matches")


def update_all_odds():
    for league_code in LEAGUES:
        try:
            update_odds_for_league(league_code)
        except Exception as e:
            print(f"{league_code}: odds update failed: {e}")
