import sqlite3
from config import DATABASE_PATH

def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_id INTEGER UNIQUE NOT NULL,
                utc_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                winner TEXT,
                score TEXT,
                status TEXT NOT NULL
            )
        """)

def save_match(match):
    with sqlite3.connect(DATABASE_PATH) as conn:

        score = f'{match["score"]["fullTime"]["home"]}:{match["score"]["fullTime"]["away"]}' if match["score"]["fullTime"]["home"] is not None else None

        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO matches (
                api_id, utc_date,home_team,away_team,winner,score,status
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            match["id"], match["utcDate"], match["homeTeam"]["shortName"], match["awayTeam"]["shortName"], match["score"]["winner"],
            score, match["status"]
        ))


if __name__ == "__main__":
    init_db()