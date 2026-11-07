# GameProphet

GameProphet is a football match prediction simulation. Ten AI agents compete to predict match outcomes across top European football leagues. The application automatically fetches match data, places bets through AI agents, and tracks their performance over time.

## Requirements

- Python 3.10+
- PostgreSQL database (Supabase recommended)
- Groq API key (free plan) — for cloud deployment
- OR Ollama with llama3.2 — for local usage
- football-data.org API key (free plan)
- the-odds-api.com API key (free plan) — for bookmaker odds

## AI Provider

GameProphet supports two AI providers:

- Ollama (local) — requires Ollama installed with llama3.2 model pulled. No API key needed. Set AI_PROVIDER=ollama in .env.
- Groq (cloud) — requires a free Groq API key from groq.com. Set AI_PROVIDER=groq in .env (default). Recommended for deployment.

## Installation

1. Clone the repository and navigate to the project folder.

2. Create and activate a virtual environment:

        python -m venv venv
        venv\Scripts\activate

3. Install dependencies:

        pip install -r requirements.txt

4. Pull the Ollama model:

        ollama pull llama3.2

5. Set up a PostgreSQL database (e.g. on Supabase) and copy the connection string.

6. Create a .env file in the root folder:

        API_KEY=your_football_data_api_key
        GROQ_API_KEY=your_groq_api_key
        AI_PROVIDER=groq
        DATABASE_URL=your_postgresql_connection_string
        ODDS_API_KEY=your_the_odds_api_key

    Optional: DISABLE_SCHEDULER=1 runs only the website, without fetching data or placing bets.

7. Run the application:

        python app.py

The scheduler will start automatically in the background.

8. Open your browser and go to http://localhost:5000

## Project Structure

- app.py — Flask backend and routes
- scheduler.py — Automatic match fetching and bet settlement
- fetcher.py — football-data.org API integration (matches, standings)
- odds_fetcher.py — the-odds-api.com integration (bookmaker odds)
- ai_agents.py — AI agent definitions, Groq/Ollama integration, bet settlement
- database.py — PostgreSQL schema and queries
- config.py — Configuration and settings
- templates/ — Jinja2 HTML templates
- static/css/style.css — Stylesheet

## Leagues

- Premier League
- Bundesliga
- Serie A
- La Liga

## AI Agents

- The Conservative — bets only on clear favorites.
- The Aggressive — high risk, high reward, never skips.
- The Analyst — weighs standings, form, odds and goals.
- The Lucky One — pure instinct, absurd reasoning.
- The Follower — backs the team higher in the table.
- The Quant — looks for value where odds look too high.
- The Momentum Trader — only backs teams on a winning streak.
- The Draw Specialist — hunts for likely draws.
- The Home Fortress — only backs home teams with strong home form.
- The Contrarian — always bets against the bookmakers' favorite.

## How It Works

1. Every hour the scheduler fetches matches (last 40 days and next 7 days) from football-data.org.
2. Once a day it fetches average bookmaker odds for matches in the next 3 days from the-odds-api.com.
3. For every upcoming match with odds, each agent gets the odds, league standings, goal averages and recent home/away form, and answers with a pick and a stake (Groq, llama-3.3-70b-versatile).
4. Each agent has a fixed budget of $1,000 per match. The dashboard tracks cumulative profit and loss starting from $0.
5. When a match finishes, bets are settled automatically using the stored odds.

## Disclaimer

GameProphet is a simulation for entertainment purposes only. This is not financial or investment advice. All predictions are made by AI agents and should not be used as a basis for real betting decisions.