from collections import defaultdict
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from config import DATABASE_URL

UPCOMING_STATUSES = ("TIMED", "SCHEDULED", "IN_PLAY", "PAUSED")
BETTABLE_STATUSES = ("TIMED", "SCHEDULED")


@contextmanager
def get_db():
    """Open a connection, commit on success, roll back on error and ALWAYS close it.

    (psycopg2's own `with conn:` only commits/rolls back — it never closes the
    connection, which leaked one connection per query.)
    """
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id SERIAL PRIMARY KEY,
                league TEXT NOT NULL,
                api_id INTEGER UNIQUE NOT NULL,
                utc_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                winner TEXT,
                score TEXT,
                status TEXT NOT NULL,
                odds_home REAL,
                odds_draw REAL,
                odds_away REAL,
                home_crest TEXT,
                away_crest TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                bet_id SERIAL PRIMARY KEY,
                agent_name TEXT NOT NULL,
                match_id INTEGER NOT NULL REFERENCES matches(match_id),
                prediction TEXT NOT NULL,
                stake_pct REAL NOT NULL,
                stake_amount REAL NOT NULL,
                reasoning TEXT,
                result TEXT,
                profit_loss REAL,
                created_at TEXT DEFAULT (now()::text),
                UNIQUE(agent_name, match_id),
                skipped BOOLEAN DEFAULT FALSE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                balance REAL NOT NULL DEFAULT 0.0,
                total_bets INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (now()::text)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_home ON matches(home_team)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_away ON matches(away_team)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_match ON bets(match_id)")


def init_agents(agents):
    with get_db() as conn:
        cursor = conn.cursor()
        for agent in agents:
            cursor.execute("""
                INSERT INTO agents (name, description)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
            """, (agent["name"], agent["description"]))


# ---------------------------------------------------------------- matches

def save_matches(matches, league_code):
    """Upsert a batch of matches from football-data.org in a single connection."""
    if not matches:
        return
    rows = []
    for match in matches:
        full_time = (match.get("score") or {}).get("fullTime") or {}
        home_goals, away_goals = full_time.get("home"), full_time.get("away")
        score = f"{home_goals}:{away_goals}" if home_goals is not None and away_goals is not None else None
        home, away = match["homeTeam"], match["awayTeam"]
        rows.append((
            league_code, match["id"], match["utcDate"],
            home.get("shortName") or home.get("name"),
            away.get("shortName") or away.get("name"),
            (match.get("score") or {}).get("winner"), score, match["status"],
            home.get("crest"), away.get("crest"),
        ))

    with get_db() as conn:
        cursor = conn.cursor()
        psycopg2.extras.execute_batch(cursor, """
            INSERT INTO matches (league, api_id, utc_date, home_team, away_team, winner, score, status, home_crest, away_crest)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_id) DO UPDATE SET
                utc_date   = EXCLUDED.utc_date,
                winner     = EXCLUDED.winner,
                score      = EXCLUDED.score,
                status     = EXCLUDED.status,
                home_crest = COALESCE(EXCLUDED.home_crest, matches.home_crest),
                away_crest = COALESCE(EXCLUDED.away_crest, matches.away_crest)
        """, rows)


def save_match(match, league_code):
    save_matches([match], league_code)


def get_upcoming_matches():
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT * FROM matches
            WHERE status = ANY(%s)
            ORDER BY utc_date
        """, (list(UPCOMING_STATUSES),))
        return [dict(row) for row in cursor.fetchall()]


def get_bettable_matches(date_to=None):
    """Matches that have not started yet (optionally only up to `date_to`, ISO string)."""
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        if date_to:
            cursor.execute("""
                SELECT * FROM matches
                WHERE status = ANY(%s) AND utc_date <= %s
                ORDER BY utc_date
            """, (list(BETTABLE_STATUSES), date_to))
        else:
            cursor.execute("""
                SELECT * FROM matches
                WHERE status = ANY(%s)
                ORDER BY utc_date
            """, (list(BETTABLE_STATUSES),))
        return [dict(row) for row in cursor.fetchall()]


def get_finished_matches():
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT * FROM matches
            WHERE status = 'FINISHED'
            ORDER BY utc_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_match_by_id(match_id):
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("SELECT * FROM matches WHERE match_id = %s", (match_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_match_by_api_id(api_id):
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("SELECT * FROM matches WHERE api_id = %s", (api_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_match_odds(updates):
    """updates: iterable of (odds_home, odds_draw, odds_away, match_id)."""
    updates = list(updates)
    if not updates:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        psycopg2.extras.execute_batch(cursor, """
            UPDATE matches
            SET odds_home = %s, odds_draw = %s, odds_away = %s
            WHERE match_id = %s
        """, updates)


# ---------------------------------------------------------------- team form

def get_team_form(team_name, limit=5):
    """Recent home games, recent away games and goal averages for a team — one connection."""
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT home_team, away_team, score, winner, utc_date
            FROM matches
            WHERE (home_team = %s OR away_team = %s)
              AND status = 'FINISHED'
              AND score IS NOT NULL
            ORDER BY utc_date DESC
        """, (team_name, team_name))
        matches = [dict(row) for row in cursor.fetchall()]

    home_games = [m for m in matches if m["home_team"] == team_name][:limit]
    away_games = [m for m in matches if m["away_team"] == team_name][:limit]

    scored, conceded = [], []
    for m in matches:
        try:
            home_goals, away_goals = map(int, m["score"].split(":"))
        except (ValueError, AttributeError):
            continue
        if m["home_team"] == team_name:
            scored.append(home_goals)
            conceded.append(away_goals)
        else:
            scored.append(away_goals)
            conceded.append(home_goals)

    stats = None
    if scored:
        stats = {
            "avg_scored": round(sum(scored) / len(scored), 2),
            "avg_conceded": round(sum(conceded) / len(conceded), 2),
            "matches_analyzed": len(scored),
        }

    return {"home_games": home_games, "away_games": away_games, "stats": stats}


# ---------------------------------------------------------------- bets

def save_bet(agent_name, match_id, prediction, stake_pct, stake_amount, reasoning, skipped=False):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bets (agent_name, match_id, prediction, stake_pct, stake_amount, reasoning, skipped)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_name, match_id) DO NOTHING
        """, (agent_name, match_id, prediction, stake_pct, stake_amount, reasoning, skipped))


def get_agents_with_bet(match_id):
    """Names of agents that already have a bet (or a skip) recorded for this match."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name FROM bets WHERE match_id = %s", (match_id,))
        return {row[0] for row in cursor.fetchall()}


def bet_exists(agent_name, match_id):
    return agent_name in get_agents_with_bet(match_id)


def get_unresolved_bets():
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT bets.*, matches.winner, matches.status,
                   matches.odds_home, matches.odds_draw, matches.odds_away
            FROM bets
            JOIN matches ON bets.match_id = matches.match_id
            WHERE bets.result IS NULL
              AND bets.skipped = FALSE
              AND matches.status = 'FINISHED'
              AND matches.winner IS NOT NULL
        """)
        return [dict(row) for row in cursor.fetchall()]


def resolve_bets(resolutions):
    """resolutions: iterable of (result, profit_loss, bet_id)."""
    resolutions = list(resolutions)
    if not resolutions:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        psycopg2.extras.execute_batch(cursor, """
            UPDATE bets
            SET result = %s, profit_loss = %s
            WHERE bet_id = %s AND result IS NULL
        """, resolutions)


def resolve_bet(bet_id, result, profit_loss):
    resolve_bets([(result, profit_loss, bet_id)])


def get_bets_for_match(match_id):
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT * FROM bets
            WHERE match_id = %s AND skipped = FALSE
            ORDER BY agent_name
        """, (match_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_agent_bets(agent_name):
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT bets.*, matches.home_team, matches.away_team,
                   matches.utc_date, matches.league, matches.score,
                   matches.winner, matches.status,
                   matches.odds_home, matches.odds_draw, matches.odds_away
            FROM bets
            JOIN matches ON bets.match_id = matches.match_id
            WHERE bets.agent_name = %s AND bets.skipped = FALSE
            ORDER BY matches.utc_date DESC
        """, (agent_name,))
        return [dict(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------- stats

def _best_streak(results):
    best = current = 0
    for r in results:
        if r == "WIN":
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def get_agents():
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT
                agents.name,
                agents.description,
                COUNT(bets.bet_id) FILTER (WHERE bets.skipped = FALSE AND bets.result IS NOT NULL) AS total_bets,
                COUNT(bets.bet_id) FILTER (WHERE bets.result = 'WIN')  AS wins,
                COUNT(bets.bet_id) FILTER (WHERE bets.result = 'LOSS') AS losses,
                COALESCE(SUM(bets.profit_loss), 0) AS balance
            FROM agents
            LEFT JOIN bets ON bets.agent_name = agents.name
            GROUP BY agents.name, agents.description
            ORDER BY balance DESC
        """)
        agents_data = cursor.fetchall()

        # Streaks follow the order in which matches were played, not when bets were stored.
        cursor.execute("""
            SELECT bets.agent_name, bets.result
            FROM bets
            JOIN matches ON bets.match_id = matches.match_id
            WHERE bets.result IS NOT NULL AND bets.skipped = FALSE
            ORDER BY bets.agent_name, matches.utc_date ASC, bets.bet_id ASC
        """)
        results_by_agent = defaultdict(list)
        for bet in cursor.fetchall():
            results_by_agent[bet["agent_name"]].append(bet["result"])

    agents = []
    for row in agents_data:
        agent = dict(row)
        agent["balance"] = float(agent["balance"] or 0)
        settled = agent["total_bets"]
        agent["win_rate"] = round(agent["wins"] / settled * 100, 1) if settled else 0.0
        agent["best_streak"] = _best_streak(results_by_agent[agent["name"]])
        agents.append(agent)
    return agents


def get_stats():
    with get_db() as conn:
        cursor = _dict_cursor(conn)
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE skipped = FALSE) AS total_bets,
                COUNT(*) FILTER (WHERE result = 'WIN')  AS total_wins,
                COUNT(*) FILTER (WHERE result = 'LOSS') AS total_losses,
                COUNT(DISTINCT match_id) AS total_matches
            FROM bets
        """)
        return dict(cursor.fetchone())


if __name__ == "__main__":
    from ai_agents import AGENTS
    init_db()
    init_agents(AGENTS)
    print("Database initialized!")
