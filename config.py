import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# football-data.org
FOOTBALL_API_KEY = os.getenv("API_KEY")

# the-odds-api.com
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

LEAGUES = {
    "PL": {
        "name": "Premier League",
        "odds_key": "soccer_epl",
    },
    "BL1": {
        "name": "Bundesliga",
        "odds_key": "soccer_germany_bundesliga",
    },
    "SA": {
        "name": "Serie A",
        "odds_key": "soccer_italy_serie_a",
    },
    "PD": {
        "name": "La Liga",
        "odds_key": "soccer_spain_la_liga",
    },
}

# "groq" (cloud) or "ollama" (local model)
AI_PROVIDER = (os.getenv("AI_PROVIDER") or os.getenv("API_PROVIDER") or "groq").strip().lower()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

OLLAMA_MODEL = "llama3.2"

# Every agent gets the same fixed budget for every match.
BUDGET_PER_MATCH = 1000

# Set DISABLE_SCHEDULER=1 to run the web app without background fetching/betting.
DISABLE_SCHEDULER = os.getenv("DISABLE_SCHEDULER", "").strip().lower() in ("1", "true", "yes")

SITE_URL = "https://gameprophet.lol"
