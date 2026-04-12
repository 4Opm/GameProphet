from fetcher import fetch_matches
from database import save_match, get_match_by_api_id
from time import sleep
from datetime import datetime, timedelta
from config import LEAGUES

from apscheduler.schedulers.background import BackgroundScheduler

from ai_agents import place_bets_for_match, settle_bets

def update_matches():
    today = datetime.now().date()
    lastWeek = today - timedelta(days=7)
    nextWeek = today + timedelta(days=7)

    for i in LEAGUES:
        results = fetch_matches(i, lastWeek.isoformat(), nextWeek.isoformat())
        bets_placed = 0
        MAX_BETS_PER_RUN = 10

        for j in results["matches"]:
            save_match(j, i)
            if j["status"] in ["TIMED", "SCHEDULED"] and bets_placed < MAX_BETS_PER_RUN:
                match = get_match_by_api_id(j["id"])
                if match:
                    place_bets_for_match(match)
                    bets_placed += 1
                    
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