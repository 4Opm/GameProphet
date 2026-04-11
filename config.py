import os

DATABASE_PATH = "football.db"
LEAGUES = ["PL","PD","BL1","SA","FL1"]
OLLAMA_MODEL = "llama3.2"

AI_PROVIDER = "groq" # "ollama" for local model

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
