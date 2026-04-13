import requests
from config import ODDS_API_KEY
from database import get_db
from thefuzz import process
import psycopg2.extras


from dotenv import load_dotenv
load_dotenv()

ODDS_API_BASE = "https://api.the-odds-api.com/v4"


LEAGUE_TO_SPORT = {
    "PL": "soccer_epl",
    "BL1": "soccer_germany_bundesliga",
    "SA": "soccer_italy_serie_a",
}

def find_matching_team(db_name, api_teams, threshold=60):
    result = process.extractOne(db_name, api_teams)
    if result and result[1] >= threshold:
        return result[0]
    return None

def update_odds_for_league(league_code):
    odds_data = fetch_odds(league_code)
    
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        updated = 0
        
        for match in odds_data:
            api_home = match["home_team"]
            api_away = match["away_team"]
            
            odds_home, odds_draw, odds_away = get_average_odds(
                match["bookmakers"], api_home, api_away
            )
            
            if not odds_home:
                continue
            
            cursor.execute("""
                SELECT match_id, home_team, away_team FROM matches
                WHERE status IN ('TIMED', 'SCHEDULED')
                AND league = %s
            """, (league_code,))
            
            db_matches = cursor.fetchall()
            
            for db_match in db_matches:
                db_home = db_match["home_team"]
                db_away = db_match["away_team"]
                
                home_match = find_matching_team(db_home, [api_home, api_away])
                away_match = find_matching_team(db_away, [api_home, api_away])
                
                if home_match == api_home and away_match == api_away:
                    cursor.execute("""
                        UPDATE matches
                        SET odds_home = %s, odds_draw = %s, odds_away = %s
                        WHERE match_id = %s
                    """, (odds_home, odds_draw, odds_away, db_match["match_id"]))
                    updated += 1
                    break
        
        print(f"{league_code}: updated odds for {updated} matches")

def fetch_odds(league_code):
    sport = LEAGUE_TO_SPORT.get(league_code)
    if not sport:
        return []
    
    response = requests.get(
        f"{ODDS_API_BASE}/sports/{sport}/odds",
        params={
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }
    )
    
    if response.status_code != 200:
        print(f"Error fetching odds for {league_code}: {response.status_code}")
        return []
    
    return response.json()

def get_average_odds(bookmakers, home_team, away_team):
    """Liczy średnią kursów ze wszystkich bukmacherów."""
    home_odds, draw_odds, away_odds = [], [], []
    
    for bookmaker in bookmakers:
        for market in bookmaker["markets"]:
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                if outcome["name"] == home_team:
                    home_odds.append(outcome["price"])
                elif outcome["name"] == away_team:
                    away_odds.append(outcome["price"])
                elif outcome["name"] == "Draw":
                    draw_odds.append(outcome["price"])
    
    return (
        round(sum(home_odds) / len(home_odds), 2) if home_odds else None,
        round(sum(draw_odds) / len(draw_odds), 2) if draw_odds else None,
        round(sum(away_odds) / len(away_odds), 2) if away_odds else None,
    )

def update_all_odds():
    for league_code in LEAGUE_TO_SPORT:
        update_odds_for_league(league_code)