import sqlite3
from config import DATABASE_PATH

def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                league TEXT NOT NULL,
                api_id INTEGER UNIQUE NOT NULL,
                utc_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                winner TEXT,
                score TEXT,
                status TEXT NOT NULL
            )
                    """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                match_id INTEGER NOT NULL REFERENCES matches(match_id),
                prediction TEXT NOT NULL,
                stake_pct REAL NOT NULL,
                stake_amount REAL NOT NULL,
                reasoning TEXT,
                result TEXT,
                profit_loss REAL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(agent_name, match_id)
            )
                    """)
        cursor.execute("""           
            CREATE TABLE IF NOT EXISTS agents (
                agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                strategy TEXT NOT NULL,
                description TEXT,
                balance REAL NOT NULL DEFAULT 10000.0,
                total_bets INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
                    """)

def save_match(match):
    with sqlite3.connect(DATABASE_PATH) as conn:

        score = f'{match["score"]["fullTime"]["home"]}:{match["score"]["fullTime"]["away"]}' if match["score"]["fullTime"]["home"] is not None else None

        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO matches (
                league, api_id, utc_date,home_team,away_team,winner,score,status
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            match["competition"]["name"],match["id"], match["utcDate"], match["homeTeam"]["shortName"], match["awayTeam"]["shortName"], match["score"]["winner"],
            score, match["status"]
        ))


def get_upcoming_matches():
    with sqlite3.connect(DATABASE_PATH) as conn:

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT * FROM matches 
                       WHERE (
                         status = 'TIMED' OR status = 'SCHEDULED'
                       ) ORDER BY (
                        utc_date
                       )
                       
                       """)
        return [dict(row) for row in cursor.fetchall()]

def get_finished_matches():
    with sqlite3.connect(DATABASE_PATH) as conn:

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
                       SELECT * FROM matches
                       WHERE status = 'FINISHED'
                       ORDER BY utc_date DESC
                       """)
        return [dict(row) for row in cursor.fetchall()]

def save_bet(agent_name, match_id, prediction, stake_pct, stake_amount, reasoning):
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO bets 
            (agent_name, match_id, prediction, stake_pct, stake_amount, reasoning)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_name, match_id, prediction, stake_pct, stake_amount, reasoning))

def init_agents(agents):
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        for agent in agents:
            cursor.execute("""
                INSERT OR IGNORE INTO agents (name, strategy, description)
                VALUES (?, ?, ?)
            """, (agent["name"], agent["strategy"], agent["description"]))

def get_agent_balance(agent_name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM agents WHERE name = ?", (agent_name,))
        row = cursor.fetchone()
        return row["balance"] if row else 10000.0

def get_team_recent_matches(team_name, limit=5):
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT home_team, away_team, score, winner, utc_date
            FROM matches
            WHERE (home_team = ? OR away_team = ?)
            AND status = 'FINISHED'
            ORDER BY utc_date DESC
            LIMIT ?
        """, (team_name, team_name, limit))
        return [dict(row) for row in cursor.fetchall()]

def bet_exists(agent_name, match_id):
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM bets 
            WHERE agent_name = ? AND match_id = ?
        """, (agent_name, match_id))
        return cursor.fetchone() is not None

def get_unresolved_bets():
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bets.*, matches.winner, matches.status
            FROM bets
            JOIN matches ON bets.match_id = matches.match_id
            WHERE bets.result IS NULL
            AND matches.status = 'FINISHED'
        """)
        return [dict(row) for row in cursor.fetchall()]

def resolve_bet(bet_id, result, profit_loss, agent_name):
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bets 
            SET result = ?, profit_loss = ?
            WHERE bet_id = ?
        """, (result, profit_loss, bet_id))
        cursor.execute("""
            UPDATE agents 
            SET balance = balance + ?,
                total_bets = total_bets + 1,
                wins = wins + ?,
                losses = losses + ?
            WHERE name = ?
        """, (profit_loss, 1 if result == 'WIN' else 0, 1 if result == 'LOSS' else 0, agent_name))

if __name__ == "__main__":
    from ai_agents import AGENTS
    init_db()
    init_agents(AGENTS)
    print("Database initialized!")