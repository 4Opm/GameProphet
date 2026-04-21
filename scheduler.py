from fetcher import fetch_matches
from database import save_match, get_match_by_api_id
from time import sleep
from datetime import datetime, timedelta
from config import LEAGUES



from apscheduler.schedulers.background import BackgroundScheduler

from ai_agents import place_bets_for_match, settle_bets

from odds_fetcher import update_all_odds

from datetime import datetime

last_odds_update = None

def update_matches():
    global last_odds_update

    today = datetime.now().date()
    lastWeek = today - timedelta(days=40)
    nextWeek = today + timedelta(days=7)

    for i in LEAGUES:
        results = fetch_matches(i, lastWeek.isoformat(), nextWeek.isoformat())
        if not results:
            print(f"No results for {i}, skipping")
            continue
        for j in results["matches"]:
            save_match(j, i)
        sleep(6)
    
    today = datetime.now().date()
    if last_odds_update != today:
        update_all_odds()
        last_odds_update = today
    
    for i in LEAGUES:
        results = fetch_matches(i, lastWeek.isoformat(), nextWeek.isoformat())
        for j in results["matches"]:
            if j["status"] in ["TIMED", "SCHEDULED"]:
                match = get_match_by_api_id(j["id"])
                if match:
                    place_bets_for_match(match)
        sleep(6)
    
    settle_bets()
    
if __name__ == "__main__":
    from database import init_db, init_agents
    from ai_agents import AGENTS
    
    init_db()
    init_agents(AGENTS)
    
    update_matches()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_matches, "interval", hours=1)
    scheduler.start()
    
    try:
        while True:
            sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()