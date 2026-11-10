# GameProphet

Ten AI agents, each with its own betting strategy, try to predict football matches in four European leagues. Every hour GameProphet fetches fixtures and results, gets real bookmaker odds, asks each agent for a pick and a stake, and settles the bets once a match ends. A leaderboard tracks which strategy actually makes money.

Leagues: Premier League, Bundesliga, Serie A, La Liga.

> GameProphet is a simulation for entertainment and learning only. No real money is involved, and nothing here is betting or financial advice.

## How it works

1. **Fixtures and results.** Every hour the scheduler downloads matches from the last 40 days and the next 14 days from [football-data.org](https://www.football-data.org/).
2. **Odds.** Once a day it gets average h2h odds from [The Odds API](https://the-odds-api.com/) for matches in the next 3 days.
3. **Predictions.** For every upcoming match that has odds, each agent receives the odds, the league standings, goal averages and recent home/away form. It answers with `HOME`, `DRAW` or `AWAY` and a stake (0% means "skip").
4. **Settlement.** Each agent has a fixed budget of **$1,000 per match**. When a match finishes, bets are settled using the stored odds, and the dashboard shows each agent's cumulative profit/loss, win rate and best streak.

Predictions come from an LLM: [Groq](https://groq.com/) (`llama-3.3-70b-versatile`, free API key) or a local [Ollama](https://ollama.com/) model (`llama3.2`, no key needed).

## The agents

| Agent | Strategy |
|---|---|
| The Conservative | Bets only on clear favorites (odds below 1.7) |
| The Aggressive | High risk, high reward, never skips |
| The Analyst | Weighs standings, form, odds and goals together |
| The Lucky One | Pure instinct, with absurd reasoning |
| The Follower | Always backs the team higher in the table |
| The Quant | Looks for value bets where the odds look too high |
| The Momentum Trader | Only backs teams on a winning streak |
| The Draw Specialist | Hunts for evenly matched games |
| The Home Fortress | Only backs home teams with strong home form |
| The Contrarian | Always bets against the bookmakers' favorite |

The agent prompts are in [`ai_agents.py`](ai_agents.py). Add or edit an entry in `AGENTS` to create your own strategy.

## Running locally

### Requirements

- Python 3.10+
- PostgreSQL: the included `docker-compose.yml` is the easiest way to get it, but any PostgreSQL works (local install, Supabase, Neon…)
- Free API keys:
  - [football-data.org](https://www.football-data.org/client/register): matches and standings
  - [The Odds API](https://the-odds-api.com/): bookmaker odds (without it agents have nothing to bet on)
  - [Groq](https://console.groq.com/keys): AI predictions. Not needed if you use Ollama.

### Setup

```bash
git clone https://github.com/4Opm/GameProphet.git
cd GameProphet

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Start a local database (or skip this and point `DATABASE_URL` at your own PostgreSQL):

```bash
docker compose up -d
```

Create your config file and fill in the API keys:

```bash
cp .env.example .env    # Windows cmd: copy .env.example .env
```

Run the app:

```bash
python app.py
```

Open http://localhost:5000. The tables are created automatically on first start. The first data update starts right away in the background and then repeats every hour. Fetching takes about half a minute, and the agents' predictions take longer, since every agent is asked about every match that has odds. Missing keys are reported in the console at startup.

### Using Ollama instead of Groq

```bash
ollama pull llama3.2
```

Then set `AI_PROVIDER=ollama` in `.env`. `GROQ_API_KEY` can stay empty.

### Configuration

All settings live in `.env` (see [`.env.example`](.env.example)):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string |
| `API_KEY` | yes | football-data.org API key |
| `ODDS_API_KEY` | yes | The Odds API key |
| `AI_PROVIDER` | no | `groq` (default) or `ollama` |
| `GROQ_API_KEY` | with Groq | Groq API key |
| `SITE_URL` | no | Public URL used in sitemap/meta tags (default `http://localhost:5000`) |
| `GA_MEASUREMENT_ID` | no | Google Analytics 4 ID; tracking is off when empty |
| `DISABLE_SCHEDULER` | no | `1` runs only the website, without fetching data or placing bets |
| `PORT` | no | Port for `python app.py` (default `5000`) |

Leagues, the per-match budget and model names are set in [`config.py`](config.py).

### Useful commands

```bash
python database.py           # create tables and agents without starting the site
python scheduler.py          # run only the background worker (no website)
python scheduler.py --once   # run a single update and exit
python test.py               # ask one agent about the next match, without saving a bet
```

## Deployment (free)

The live site at [gameprophet.lol](https://gameprophet.lol) runs on free plans only. The website and the hourly update run separately, because free web hosts go to sleep when nobody visits:

| Part | Service | Notes |
|---|---|---|
| Website | [Render](https://render.com) free web service | Sleeps after 15 min without traffic; the first visit after that takes up to a minute |
| Database | [Neon](https://neon.com) free Postgres | Scales to zero when idle, never expires |
| Hourly update | GitHub Actions ([`update.yml`](.github/workflows/update.yml)) | Runs `python scheduler.py --once` every hour |

### 1. Database (Neon)

Create a project on Neon, open **Connect**, tick **Show password** and copy the connection string. That string is your `DATABASE_URL`. Tables are created automatically on the first run.

### 2. Hourly update (GitHub Actions)

In the repository go to **Settings → Secrets and variables → Actions** and add these secrets:

`DATABASE_URL`, `API_KEY`, `ODDS_API_KEY`, `GROQ_API_KEY`

Then open the **Actions** tab, choose **Update matches** and click **Run workflow** to test it. After that it runs every hour on its own.

> GitHub turns off scheduled workflows in public repositories after 60 days without any activity in the repo. If updates stop, open the Actions tab and enable the workflow again.

### 3. Website (Render)

1. On Render choose **New → Blueprint** and select this repository. [`render.yaml`](render.yaml) sets up a free web service with the scheduler turned off.
2. When asked, paste `DATABASE_URL` (and optionally `GA_MEASUREMENT_ID`).
3. Under **Settings → Custom Domains** add your domain and create the DNS records Render shows you at your domain registrar. HTTPS is set up automatically.

If you fork the project, change `SITE_URL` in `render.yaml` to your own domain, and change the repository name in the `if:` line of `update.yml`.

### Other hosts

Any host that can run Python works. On an always-on server you can skip GitHub Actions and let the app run the scheduler itself (leave `DISABLE_SCHEDULER` unset). The `Procfile` does exactly that:

```
web: gunicorn app:app --timeout 120 --workers 1
```

Keep `--workers 1` in that setup: each worker would start its own scheduler, which doubles API calls and LLM requests.

## Project structure

```
app.py            Flask routes, sitemap, robots.txt
scheduler.py      Hourly job: fetch matches -> settle bets -> update odds -> place bets
render.yaml       Render config for the website
.github/workflows GitHub Actions hourly update
fetcher.py        football-data.org client (matches, cached standings)
odds_fetcher.py   The Odds API client + fuzzy team-name matching
ai_agents.py      Agent definitions, LLM calls, response parsing, bet settlement
database.py       PostgreSQL schema and queries
config.py         Settings loaded from .env
templates/        Jinja2 templates
static/           CSS, JavaScript, images
```

## Data sources and limits

- football-data.org's free plan allows 10 requests per minute. The scheduler waits 6 seconds between leagues and caches standings for an hour.
- The Odds API's free plan has a monthly request quota. Odds are fetched once per day (4 requests).
- Team names differ between the two APIs, so they are matched with fuzzy string matching (`thefuzz`).

## License

[MIT](LICENSE)
