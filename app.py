from flask import Flask, jsonify, render_template
from database import get_upcoming_matches, get_finished_matches
from database import get_upcoming_matches, get_finished_matches, get_agents
from database import get_upcoming_matches, get_finished_matches, get_agents, get_bets_for_match, get_match_by_id

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello world!'

@app.route('/upcoming')
def upcoming_matches():
    return render_template("upcoming.html", matches = get_upcoming_matches())

@app.route('/finished')
def finished_matches():
    return render_template("finished.html", matches = get_finished_matches())

@app.route('/dashboard')
def dashboard():
    agents = get_agents()
    return render_template('dashboard.html', agents=agents)

@app.route('/match/<int:match_id>')
def match_detail(match_id):
    match = get_match_by_id(match_id)
    bets = get_bets_for_match(match_id)
    return render_template('match.html', match=match, bets=bets)

if __name__ == '__main__':
    app.run()