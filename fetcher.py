import requests, json, os
from dotenv import load_dotenv
from datetime import datetime, timedelta


load_dotenv()
API_KEY = os.getenv("API_KEY")

headers = {
    "X-Auth-Token": API_KEY
}


def fetch_matches(league_code, date_from, date_to):

    url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"

    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return(response.json())
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return None
    except requests.exceptions.ConnectionError:
        print("No connection to API")
        return None
    
def fetch_standings(league_code):
    url = f"https://api.football-data.org/v4/competitions/{league_code}/standings"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching standings for {league_code}: {response.status_code}")
        return None
    
    return response.json()

def get_standings_dict(league_code):
    data = fetch_standings(league_code)
    if not data:
        return {}
    
    standings = {}
    for entry in data["standings"][0]["table"]:
        short_name = entry["team"]["shortName"]
        standings[short_name] = {
            "position": entry["position"],
            "points": entry["points"],
            "played": entry["playedGames"],
            "won": entry["won"],
            "draw": entry["draw"],
            "lost": entry["lost"],
            "goal_difference": entry["goalDifference"]
        }
    
    return standings