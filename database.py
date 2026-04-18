import psycopg2
import psycopg2.extras
from config import DATABASE_URL

def get_db():
    return psycopg2.connect(DATABASE_URL)

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
                odds_away REAL
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
                UNIQUE(agent_name, match_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                strategy TEXT NOT NULL,
                description TEXT,
                balance REAL NOT NULL DEFAULT 0.0,
                total_bets INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (now()::text)
            )
        """)

def save_match(match, league_code):
    with get_db() as conn:
        cursor = conn.cursor()
        score = f'{match["score"]["fullTime"]["home"]}:{match["score"]["fullTime"]["away"]}' if match["score"]["fullTime"]["home"] is not None else None
        cursor.execute("""
            INSERT INTO matches (league, api_id, utc_date, home_team, away_team, winner, score, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_id) DO UPDATE SET
                winner = EXCLUDED.winner,
                score = EXCLUDED.score,
                status = EXCLUDED.status
        """, (league_code, match["id"], match["utcDate"], match["homeTeam"]["shortName"], match["awayTeam"]["shortName"], match["score"]["winner"], score, match["status"]))

def get_upcoming_matches():
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM matches
            WHERE status = 'TIMED' OR status = 'SCHEDULED'
            ORDER BY utc_date
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_finished_matches():
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM matches
            WHERE status = 'FINISHED'
            ORDER BY utc_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def save_bet(agent_name, match_id, prediction, stake_pct, stake_amount, reasoning):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bets (agent_name, match_id, prediction, stake_pct, stake_amount, reasoning)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_name, match_id) DO NOTHING
        """, (agent_name, match_id, prediction, stake_pct, stake_amount, reasoning))

def init_agents(agents):
    with get_db() as conn:
        cursor = conn.cursor()
        for agent in agents:
            cursor.execute("""
                INSERT INTO agents (name, strategy, description, balance)
                VALUES (%s, %s, %s, 0)
                ON CONFLICT (name) DO NOTHING
            """, (agent["name"], agent["strategy"], agent["description"]))

def get_agent_balance(agent_name):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT balance FROM agents WHERE name = %s", (agent_name,))
        row = cursor.fetchone()
        return row["balance"] if row else 10000.0

def get_team_recent_matches(team_name, limit=10):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT home_team, away_team, score, winner, utc_date
            FROM matches
            WHERE (home_team = %s OR away_team = %s)
            AND status = 'FINISHED'
            ORDER BY utc_date DESC
            LIMIT %s
        """, (team_name, team_name, limit))
        return [dict(row) for row in cursor.fetchall()]

def bet_exists(agent_name, match_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM bets
            WHERE agent_name = %s AND match_id = %s
        """, (agent_name, match_id))
        return cursor.fetchone() is not None

def get_unresolved_bets():
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT bets.*, matches.winner, matches.status,
                   matches.odds_home, matches.odds_draw, matches.odds_away
            FROM bets
            JOIN matches ON bets.match_id = matches.match_id
            WHERE bets.result IS NULL
            AND matches.status = 'FINISHED'
        """)
        return [dict(row) for row in cursor.fetchall()]

def resolve_bet(bet_id, result, profit_loss, agent_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bets
            SET result = %s, profit_loss = %s
            WHERE bet_id = %s
        """, (result, profit_loss, bet_id))
        cursor.execute("""
            UPDATE agents
            SET balance = balance + %s,
                total_bets = total_bets + 1,
                wins = wins + %s,
                losses = losses + %s
            WHERE name = %s
        """, (profit_loss, 1 if result == 'WIN' else 0, 1 if result == 'LOSS' else 0, agent_name))

def get_match_by_api_id(api_id):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM matches WHERE api_id = %s", (api_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_agents():
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT *,
            CASE WHEN total_bets > 0 
            THEN ROUND((CAST(wins AS FLOAT) / CAST(total_bets AS FLOAT) * 100)::numeric, 1)
            ELSE NULL END as win_rate
            FROM agents
            ORDER BY balance DESC
        """)
        result = []
        for row in cursor.fetchall():
            r = dict(row)
            r['win_rate'] = float(r['win_rate']) if r['win_rate'] else None
            result.append(r)
        return result

def get_bets_for_match(match_id):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM bets WHERE match_id = %s", (match_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_match_by_id(match_id):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM matches WHERE match_id = %s", (match_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_team_home_matches(team_name, limit=5):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT home_team, away_team, score, winner, utc_date
            FROM matches
            WHERE home_team = %s
            AND status = 'FINISHED'
            ORDER BY utc_date DESC
            LIMIT %s
        """, (team_name, limit))
        return [dict(row) for row in cursor.fetchall()]

def get_team_away_matches(team_name, limit=5):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT home_team, away_team, score, winner, utc_date
            FROM matches
            WHERE away_team = %s
            AND status = 'FINISHED'
            ORDER BY utc_date DESC
            LIMIT %s
        """, (team_name, limit))
        return [dict(row) for row in cursor.fetchall()]

def get_agent_bets(agent_name):
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT bets.*, matches.home_team, matches.away_team, 
                   matches.utc_date, matches.league, matches.score,
                   matches.winner, matches.status,
                   matches.odds_home, matches.odds_draw, matches.odds_away
            FROM bets
            JOIN matches ON bets.match_id = matches.match_id
            WHERE bets.agent_name = %s
            ORDER BY matches.utc_date DESC
        """, (agent_name,))
        return [dict(row) for row in cursor.fetchall()]
if __name__ == "__main__":
    from ai_agents import AGENTS
    init_db()
    init_agents(AGENTS)
    print("Database initialized!")