import os
from urllib.parse import quote
from xml.sax.saxutils import escape

from flask import Flask, Response, abort, render_template
from flask_caching import Cache

from ai_agents import AGENT_NAMES, AGENTS
from config import DISABLE_SCHEDULER, LEAGUES, SITE_URL
from database import (
    get_agent_bets,
    get_agents,
    get_bets_for_match,
    get_finished_matches,
    get_match_by_id,
    get_stats,
    get_upcoming_matches,
    init_agents,
    init_db,
)

app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})

try:
    init_db()
    init_agents(AGENTS)
except Exception as e:  # don't crash the whole site if the DB is briefly unavailable at boot
    print(f"Database init failed: {e}")

if not DISABLE_SCHEDULER:
    from scheduler import start_scheduler
    start_scheduler()


@app.context_processor
def inject_globals():
    return {"site_url": SITE_URL}


@app.route("/")
@cache.cached(timeout=300)
def index():
    return render_template("index.html", active_page="home", stats=get_stats(),
                           agent_count=len(AGENTS), league_count=len(LEAGUES))


@app.route("/upcoming")
@cache.cached(timeout=300)
def upcoming_matches():
    return render_template("upcoming.html", matches=get_upcoming_matches(), leagues=LEAGUES, active_page="upcoming")


@app.route("/finished")
@cache.cached(timeout=300)
def finished_matches():
    return render_template("finished.html", matches=get_finished_matches(), leagues=LEAGUES, active_page="finished")


@app.route("/dashboard")
@cache.cached(timeout=300)
def dashboard():
    return render_template("dashboard.html", agents=get_agents(), active_page="dashboard")


@app.route("/faq")
def faq():
    return render_template("faq.html", active_page="faq")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", active_page="privacy")


@app.route("/agent/<agent_name>")
@cache.cached(timeout=300)
def agent_detail(agent_name):
    if agent_name not in AGENT_NAMES:
        abort(404)
    return render_template("agent.html", agent_name=agent_name, bets=get_agent_bets(agent_name),
                           active_page="dashboard")


@app.route("/match/<int:match_id>")
@cache.cached(timeout=300)
def match_detail(match_id):
    match = get_match_by_id(match_id)
    if match is None:
        abort(404)
    return render_template("match.html", match=match, bets=get_bets_for_match(match_id))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


SITEMAP_PAGES = [
    ("/", "daily", "1.0"),
    ("/upcoming", "hourly", "0.9"),
    ("/finished", "hourly", "0.9"),
    ("/dashboard", "hourly", "0.8"),
    ("/faq", "monthly", "0.5"),
    ("/privacy", "monthly", "0.3"),
]


@app.route("/sitemap.xml")
@cache.cached(timeout=3600)
def sitemap():
    entries = list(SITEMAP_PAGES)
    entries += [(f"/agent/{quote(name)}", "daily", "0.6") for name in AGENT_NAMES]
    try:
        entries += [(f"/match/{m['match_id']}", "daily", "0.5") for m in get_upcoming_matches()]
        entries += [(f"/match/{m['match_id']}", "weekly", "0.4") for m in get_finished_matches()]
    except Exception as e:
        print(f"Sitemap: could not load matches: {e}")

    urls = "\n".join(
        f"  <url>\n    <loc>{escape(SITE_URL + path)}</loc>\n"
        f"    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>\n  </url>"
        for path, freq, priority in entries
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{urls}\n</urlset>")
    return Response(xml, mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    txt = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(txt, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
