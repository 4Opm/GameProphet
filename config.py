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

# Public URL of the site (used in sitemap, robots.txt and social meta tags).
SITE_URL = (os.getenv("SITE_URL") or "http://localhost:5000").rstrip("/")

# Optional Google Analytics 4 measurement ID (e.g. G-XXXXXXXXXX). Leave empty to disable tracking.
GA_MEASUREMENT_ID = (os.getenv("GA_MEASUREMENT_ID") or "").strip()


def config_problems():
    """Human-readable list of missing settings, printed at startup."""
    problems = []
    if not DATABASE_URL:
        problems.append("DATABASE_URL is not set - copy .env.example to .env (and run `docker compose up -d` for a local database).")
    if DISABLE_SCHEDULER:
        return problems
    if not FOOTBALL_API_KEY:
        problems.append("API_KEY (football-data.org) is not set - no matches will be fetched.")
    if not ODDS_API_KEY:
        problems.append("ODDS_API_KEY (the-odds-api.com) is not set - no odds, so agents will not place bets.")
    if AI_PROVIDER == "groq" and not GROQ_API_KEY:
        problems.append("GROQ_API_KEY is not set - set it, or use AI_PROVIDER=ollama with a local Ollama model.")
    if AI_PROVIDER not in ("groq", "ollama"):
        problems.append(f"AI_PROVIDER={AI_PROVIDER!r} is not supported - use 'groq' or 'ollama'.")
    return problems
