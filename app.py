from flask import Flask, jsonify, render_template
from database import get_upcoming_matches, get_finished_matches

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


if __name__ == '__main__':
    app.run()