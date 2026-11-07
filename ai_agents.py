import re
import time

from config import AI_PROVIDER, BUDGET_PER_MATCH, GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL
from database import (
    get_agents_with_bet,
    get_team_form,
    get_unresolved_bets,
    resolve_bets,
    save_bet,
)
from fetcher import get_standings_dict

VALID_PREDICTIONS = ("HOME", "DRAW", "AWAY")
MAX_ATTEMPTS = 3

AGENTS = [
    {
        "name": "The Conservative",
        "description": "Bets only on clear favorites with small stakes",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You only bet on clear favorites. Analyze the odds — only bet if one team has odds below 1.7.
Adjust your stake based on confidence:
- Very confident (odds below 1.4): stake 40-60%
- Confident (odds 1.4-1.6): stake 20-35%
- Somewhat confident (odds 1.6-1.7): stake 5-15%
- Not confident enough: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 60)
REASONING: (one sentence explanation or skip)"""
    },
    {
        "name": "The Aggressive",
        "description": "High risk, high reward, bets big on gut feeling",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You love risk and always bet big. Never skip a match.
Adjust your stake based on how exciting the match looks:
- Very exciting or high stakes match: stake 70-100%
- Interesting match: stake 40-65%
- Regular match: stake 20-35%
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 20 and 100)
REASONING: (one sentence explanation)"""
    },
    {
        "name": "The Analyst",
        "description": "Analyzes all data carefully before betting",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You analyze all available data — standings, form, odds, goals scored and conceded — before making a decision.
Adjust your stake based on how clear the data is:
- All data points to same outcome: stake 40-55%
- Most data points to same outcome: stake 20-35%
- Data is mixed: stake 5-15%
- Data is inconclusive: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 55)
REASONING: (one sentence explanation or skip)"""
    },
    {
        "name": "The Lucky One",
        "description": "Bets purely on instinct and luck, no logic",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You ignore all data and bet purely on instinct and luck. Never skip a match.
Vary your stake randomly and unpredictably:
- Sometimes go all in: stake 80-100%
- Sometimes bet medium: stake 30-60%
- Sometimes bet small: stake 5-20%
Your reasoning should be completely absurd and unrelated to football.
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 5 and 100)
REASONING: (one completely absurd sentence unrelated to football)"""
    },
    {
        "name": "The Follower",
        "description": "Always bets on the team higher in the league standings",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You always bet on the team with the better position in the league standings. If standings are unavailable, bet on the home team.
Adjust your stake based on the gap in standings:
- Gap of 8+ positions: stake 50-65%
- Gap of 4-7 positions: stake 25-40%
- Gap of 1-3 positions: stake 10-20%
- Same position or no data: stake 5-10%
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 5 and 65)
REASONING: (one sentence explanation)"""
    },
    {
        "name": "The Quant",
        "description": "Looks for value bets where odds seem too high",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You only bet when you believe the odds are higher than they should be — value betting.
Compare the odds to the team's recent form and standings to find mispriced bets.
Adjust your stake based on how much value you see:
- Huge value (odds much higher than expected): stake 45-60%
- Good value (odds slightly higher than expected): stake 20-40%
- Some value: stake 5-15%
- No value found: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 60)
REASONING: (one sentence explanation or skip)"""
    },
    {
        "name": "The Momentum Trader",
        "description": "Only bets on teams on a winning streak",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You only bet on teams that are on a winning streak. Check the recent home and away form carefully.
Adjust your stake based on the length of the winning streak:
- Team won last 4+ matches: stake 45-60%
- Team won last 3 matches: stake 25-40%
- Team won last 2 matches: stake 10-20%
- No clear winning streak: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 60)
REASONING: (one sentence explanation or skip)"""
    },
    {
        "name": "The Draw Specialist",
        "description": "Looks for matches likely to end in a draw",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You specialize in finding matches likely to end in a draw. Look for:
- Both teams with similar standings and form
- Draw odds between 2.8 and 3.5
- Both teams scoring and conceding similar number of goals
- Recent matches between evenly matched teams
Adjust your stake based on confidence:
- Very strong draw signals: stake 40-55%
- Good draw signals: stake 20-35%
- Some draw signals: stake 5-15%
- No draw signals: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 55)
REASONING: (one sentence explanation or skip)"""
    },
    {
        "name": "The Home Fortress",
        "description": "Only bets on home teams with strong home form",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You only bet on home teams that have a strong home record. Check the recent HOME games of the home team carefully.
Adjust your stake based on home form:
- Home team won last 4+ home games: stake 45-60%
- Home team won last 3 home games: stake 25-40%
- Home team won last 2 home games: stake 10-20%
- Home form is weak or unclear: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 60)
REASONING: (one sentence explanation or skip)"""
    },
    {
    "name": "The Contrarian",
        "description": "Always bets against what the odds suggest",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You always bet against what the bookmakers suggest. If odds say HOME is favorite, you bet AWAY or DRAW.
You believe bookmakers are always wrong and the underdog is undervalued.
Adjust your stake based on how strongly the odds favor the favorite:
- Odds heavily favor one team (below 1.5): stake 45-60% on the other side
- Odds moderately favor one team (1.5-2.0): stake 20-40% on the other side
- Odds are fairly even: stake 5-15% on the away team
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 5 and 60)
REASONING: (one sentence explanation)"""
    }
]


AGENT_NAMES = [agent["name"] for agent in AGENTS]


# ---------------------------------------------------------------- LLM

_groq_client = None


def _ask_llm(messages):
    global _groq_client
    if AI_PROVIDER == "groq":
        if _groq_client is None:
            from groq import Groq
            _groq_client = Groq(api_key=GROQ_API_KEY, timeout=60)
        response = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content or ""

    import ollama
    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    return response["message"]["content"] or ""


# ---------------------------------------------------------------- match context

def _format_recent(matches):
    if not matches:
        return "No data available"
    return "\n".join(
        f"  {m['home_team']} vs {m['away_team']} | Score: {m['score']} | Winner: {m['winner']}"
        for m in matches
    )


def _format_standing(standing, team_name):
    if not standing:
        return f"No standings data for {team_name}"
    return (f"Position: {standing['position']} | Points: {standing['points']} | "
            f"W{standing['won']} D{standing['draw']} L{standing['lost']} | GD: {standing['goal_difference']}")


def _format_stats(team, stats):
    if not stats:
        return f"{team} stats: no finished matches yet"
    return (f"{team} stats (last {stats['matches_analyzed']} matches):\n"
            f"Avg goals scored: {stats['avg_scored']} | Avg goals conceded: {stats['avg_conceded']}")


def build_match_info(match):
    """Everything the agents get to see about a match. Built once per match and shared by all agents."""
    home, away = match["home_team"], match["away_team"]
    home_form = get_team_form(home)
    away_form = get_team_form(away)
    standings = get_standings_dict(match["league"])

    def odd(key):
        return match.get(key) or "N/A"

    return f"""
Match: {home} vs {away}
League: {match['league']}
Date: {match['utc_date']}
Odds: Home {odd('odds_home')} | Draw {odd('odds_draw')} | Away {odd('odds_away')}

League standings:
{home}: {_format_standing(standings.get(home), home)}
{away}: {_format_standing(standings.get(away), away)}

{_format_stats(home, home_form['stats'])}

{_format_stats(away, away_form['stats'])}

{home} recent HOME games:
{_format_recent(home_form['home_games'])}

{home} recent AWAY games:
{_format_recent(home_form['away_games'])}

{away} recent HOME games:
{_format_recent(away_form['home_games'])}

{away} recent AWAY games:
{_format_recent(away_form['away_games'])}
"""


def get_agent_prediction(agent, match, match_info=None):
    if match_info is None:
        match_info = build_match_info(match)
    messages = [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": f"Analyze this match and make your prediction:\n{match_info}"},
    ]
    return _ask_llm(messages)


# ---------------------------------------------------------------- parsing

_FIELD_RE = re.compile(r"^[\s*_#>-]*(PREDICTION|STAKE_PCT|STAKE|REASONING)[\s*_]*[:=][\s*_]*(.*)$", re.IGNORECASE)
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_ALIASES = {
    "1": "HOME", "HOME TEAM": "HOME", "HOME_TEAM": "HOME",
    "X": "DRAW", "TIE": "DRAW",
    "2": "AWAY", "AWAY TEAM": "AWAY", "AWAY_TEAM": "AWAY",
}


def _normalize_prediction(value):
    value = value.strip().strip("*_.\"' ").upper()
    if value in _ALIASES:
        return _ALIASES[value]
    for option in VALID_PREDICTIONS:
        if value.startswith(option):
            return option
    return None


def parse_prediction(response_text):
    """Parse the LLM answer. Tolerates markdown (**PREDICTION:**), lowercase, '%' signs etc."""
    result = {"prediction": None, "stake_pct": None, "reasoning": None}

    for line in (response_text or "").strip().splitlines():
        m = _FIELD_RE.match(line)
        if not m:
            continue
        field, value = m.group(1).upper(), m.group(2).strip()
        if field == "PREDICTION":
            result["prediction"] = _normalize_prediction(value)
        elif field in ("STAKE_PCT", "STAKE"):
            number = _NUMBER_RE.search(value)
            if number:
                result["stake_pct"] = max(0.0, min(100.0, float(number.group().replace(",", "."))))
        elif field == "REASONING":
            reasoning = value.strip("*_ ").strip()
            result["reasoning"] = None if not reasoning or reasoning.lower().rstrip(".") == "skip" else reasoning

    return result


def _is_valid(parsed):
    return parsed["stake_pct"] == 0 or (parsed["prediction"] is not None and parsed["stake_pct"] is not None)


# ---------------------------------------------------------------- betting

def place_bets_for_match(match):
    if not (match.get("odds_home") and match.get("odds_draw") and match.get("odds_away")):
        print(f"No odds available for {match['home_team']} vs {match['away_team']}, skipping")
        return

    already_bet = get_agents_with_bet(match["match_id"])
    pending_agents = [a for a in AGENTS if a["name"] not in already_bet]
    if not pending_agents:
        return

    match_info = build_match_info(match)

    for agent in pending_agents:
        parsed = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                candidate = parse_prediction(get_agent_prediction(agent, match, match_info))
                if _is_valid(candidate):
                    parsed = candidate
                    break
                print(f"{agent['name']}: invalid response on attempt {attempt}, retrying...")
            except Exception as e:
                print(f"{agent['name']}: error on attempt {attempt}: {e}")
            time.sleep(2 * attempt)

        if parsed is None:
            print(f"{agent['name']}: failed after {MAX_ATTEMPTS} attempts, skipping")
            continue

        if parsed["stake_pct"] == 0:
            print(f"{agent['name']}: decided to skip this match")
            save_bet(
                agent_name=agent["name"],
                match_id=match["match_id"],
                prediction=parsed["prediction"] or "DRAW",
                stake_pct=0,
                stake_amount=0,
                reasoning=None,
                skipped=True,
            )
            continue

        stake_amount = round(BUDGET_PER_MATCH * parsed["stake_pct"] / 100, 2)
        print(f"{agent['name']}: {parsed['prediction']} | {parsed['stake_pct']}% | ${stake_amount:.2f}")

        save_bet(
            agent_name=agent["name"],
            match_id=match["match_id"],
            prediction=parsed["prediction"],
            stake_pct=parsed["stake_pct"],
            stake_amount=stake_amount,
            reasoning=parsed["reasoning"],
        )
        time.sleep(3)


WINNER_FOR_PREDICTION = {"HOME": "HOME_TEAM", "AWAY": "AWAY_TEAM", "DRAW": "DRAW"}
ODDS_COLUMN = {"HOME": "odds_home", "AWAY": "odds_away", "DRAW": "odds_draw"}
DEFAULT_ODDS = {"HOME": 2.0, "AWAY": 2.0, "DRAW": 3.0}


def settle_bet(bet):
    """Return (result, profit_loss) for a bet on a finished match."""
    prediction = bet["prediction"]
    stake = bet["stake_amount"]
    odds = bet.get(ODDS_COLUMN.get(prediction, "odds_draw")) or DEFAULT_ODDS.get(prediction, 2.0)

    if WINNER_FOR_PREDICTION.get(prediction) == bet["winner"]:
        return "WIN", round(stake * odds - stake, 2)
    return "LOSS", round(-stake, 2)


def settle_bets():
    unresolved = get_unresolved_bets()
    if not unresolved:
        print("No unresolved bets found")
        return

    resolutions = []
    for bet in unresolved:
        result, profit_loss = settle_bet(bet)
        print(f"{bet['agent_name']}: {bet['prediction']} vs {bet['winner']} -> {result} | ${profit_loss:.2f}")
        resolutions.append((result, profit_loss, bet["bet_id"]))

    resolve_bets(resolutions)
