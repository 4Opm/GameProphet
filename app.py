from flask import Flask, jsonify, render_template, redirect, url_for
from flask_caching import Cache
from database import get_upcoming_matches, get_finished_matches, get_agents, get_bets_for_match, get_match_by_id, get_agent_bets

from database import init_db, init_agents
from ai_agents import AGENTS

import threading
from scheduler import update_matches



app = Flask(__name__)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

init_db()
init_agents(AGENTS)

def run_scheduler():
    update_matches()
    from apscheduler.schedulers.background import BackgroundScheduler
    from time import sleep
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_matches, "interval", hours=1)
    scheduler.start()

thread = threading.Thread(target=run_scheduler, daemon=True)
thread.start()

@app.route('/')
def index():
    return render_template('index.html', active_page='home')

@app.route('/upcoming')
@cache.cached(timeout=300)
def upcoming_matches():
    matches = get_upcoming_matches()
    return render_template("upcoming.html", matches=matches, active_page='upcoming')

@app.route('/finished')
@cache.cached(timeout=300)
def finished_matches():
    matches = get_finished_matches()
    return render_template("finished.html", matches=matches, active_page='finished')

@app.route('/dashboard')
@cache.cached(timeout=300)
def dashboard():
    agents = get_agents()
    return render_template('dashboard.html', agents=agents, active_page='dashboard')

@app.route('/faq')
def faq():
    return render_template('faq.html', active_page='faq')

@app.route('/agent/<agent_name>')
@cache.cached(timeout=300, key_prefix='agent_%s')
def agent_detail(agent_name):
    bets = get_agent_bets(agent_name)
    return render_template('agent.html', agent_name=agent_name, bets=bets)

@app.route('/match/<int:match_id>')
@cache.cached(timeout=300, key_prefix='match_%s')
def match_detail(match_id):
    match = get_match_by_id(match_id)
    bets = get_bets_for_match(match_id)
    return render_template('match.html', match=match, bets=bets)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)