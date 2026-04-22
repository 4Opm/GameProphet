import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

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

OLLAMA_MODEL = "llama3.2"

AI_PROVIDER = "groq" # "ollama" for local model

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

ODDS_API_KEY = os.getenv("ODDS_API_KEY")