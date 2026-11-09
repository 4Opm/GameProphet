import threading
from datetime import datetime, timedelta, timezone
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler

from ai_agents import place_bets_for_match, settle_bets
from config import LEAGUES
from database import get_bettable_matches, save_matches
from fetcher import fetch_matches
from odds_fetcher import update_all_odds

DAYS_BACK = 40
DAYS_AHEAD = 14  # long enough to bridge international breaks; bets still need odds (next 3 days)
API_PAUSE_SECONDS = 6  # football-data.org free tier: 10 requests / minute

_last_odds_update = None
_run_lock = threading.Lock()


def update_matches():
    """Fetch fixtures/results, refresh odds once a day, place new bets and settle finished ones."""
    global _last_odds_update

    if not _run_lock.acquire(blocking=False):
        print("Previous update still running, skipping this run")
        return

    try:
        today = datetime.now(timezone.utc).date()
        date_from = (today - timedelta(days=DAYS_BACK)).isoformat()
        date_to = (today + timedelta(days=DAYS_AHEAD)).isoformat()

        for league_code in LEAGUES:
            results = fetch_matches(league_code, date_from, date_to)
            if not results or "matches" not in results:
                print(f"No results for {league_code}, skipping")
            else:
                save_matches(results["matches"], league_code)
                print(f"{league_code}: saved {len(results['matches'])} matches")
            sleep(API_PAUSE_SECONDS)

        # Settle first so the leaderboard is up to date even if betting fails later.
        settle_bets()

        if _last_odds_update != today:
            update_all_odds()
            _last_odds_update = today

        for match in get_bettable_matches():
            try:
                place_bets_for_match(match)
            except Exception as e:
                print(f"Betting failed for match {match['match_id']}: {e}")
    finally:
        _run_lock.release()


def safe_update_matches():
    try:
        update_matches()
    except Exception as e:
        print(f"Scheduler error: {e}")


def start_scheduler():
    """Run one update now (in the background) and then every hour."""
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        safe_update_matches,
        "interval",
        hours=1,
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler


if __name__ == "__main__":
    from ai_agents import AGENTS
    from database import init_agents, init_db

    init_db()
    init_agents(AGENTS)

    scheduler = start_scheduler()
    try:
        while True:
            sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
