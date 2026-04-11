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