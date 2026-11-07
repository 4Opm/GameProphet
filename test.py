"""Manual smoke test: ask the first agent for a prediction on the next upcoming match.

Usage: python test.py   (calls the real LLM API, does NOT save a bet)
"""
from ai_agents import AGENTS, get_agent_prediction, parse_prediction
from database import get_bettable_matches

if __name__ == "__main__":
    matches = get_bettable_matches()
    if not matches:
        print("No upcoming matches in the database.")
    else:
        match = matches[0]
        print(f"{match['home_team']} vs {match['away_team']}\n")
        response = get_agent_prediction(AGENTS[0], match)
        print(response)
        print("\nParsed:", parse_prediction(response))
