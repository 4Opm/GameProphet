from fetcher import fetch_matches
from database import save_match, init_db
from time import sleep
from datetime import datetime, timedelta
from config import LEAGUES

from apscheduler.schedulers.background import BackgroundScheduler

def update_matches():
    today = datetime.now().date()
    lastWeek = today - timedelta(days=7)
    nextWeek = today + timedelta(days=7)

    for i in LEAGUES:
        results = fetch_matches(i, lastWeek.isoformat(), nextWeek.isoformat())
        for j in results["matches"]:
            save_match(j)
        sleep(6)
    
if __name__ == "__main__":
    init_db()
    update_matches()

    scheduler = BackgroundScheduler()
    scheduler.add_job(update_matches, "interval", hours=1)
    scheduler.start()

    try:
        while True:
            sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()