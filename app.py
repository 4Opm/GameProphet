from flask import Flask, render_template
from flask_caching import Cache
from database import get_upcoming_matches, get_finished_matches, get_agents, get_bets_for_match, get_match_by_id, get_agent_bets, get_stats

from database import init_db, init_agents
from ai_agents import AGENTS

import threading
from scheduler import update_matches

from config import LEAGUES

app = Flask(__name__)

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

init_db()
init_agents(AGENTS)

def run_scheduler():
    try:
        update_matches()
    except Exception as e:
        print(f"Scheduler error: {e}")
    
    from apscheduler.schedulers.background import BackgroundScheduler
    from time import sleep
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_matches, "interval", hours=1)
    scheduler.start()
    
    try:
        while True:
            sleep(60)
    except Exception as e:
        print(f"Scheduler stopped: {e}")

thread = threading.Thread(target=run_scheduler, daemon=True)
thread.start()

@app.route('/')
def index():
    stats = get_stats()
    return render_template('index.html', active_page='home', stats=stats)

@app.route('/upcoming')
@cache.cached(timeout=300)
def upcoming_matches():
    matches = get_upcoming_matches()
    return render_template("upcoming.html", matches=matches, leagues=LEAGUES, active_page='upcoming')

@app.route('/finished')
@cache.cached(timeout=300)
def finished_matches():
    matches = get_finished_matches()
    return render_template("finished.html", matches=matches, leagues=LEAGUES, active_page='finished')

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

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', active_page='privacy')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

from flask import Response

@app.route('/sitemap.xml')
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://gameprophet.up.railway.app/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/upcoming</loc>
        <changefreq>hourly</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/finished</loc>
        <changefreq>hourly</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/dashboard</loc>
        <changefreq>hourly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/faq</loc>
        <changefreq>monthly</changefreq>
        <priority>0.5</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/privacy</loc>
        <changefreq>monthly</changefreq>
        <priority>0.3</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Conservative</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Aggressive</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Analyst</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Lucky%20One</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Follower</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Quant</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Momentum%20Trader</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Draw%20Specialist</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Home%20Fortress</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
    <url>
        <loc>https://gameprophet.up.railway.app/agent/The%20Contrarian</loc>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
</urlset>'''
    return Response(xml, mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    txt = '''User-agent: *
Allow: /
Sitemap: https://gameprophet.up.railway.app/sitemap.xml'''
    return Response(txt, mimetype='text/plain')

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)