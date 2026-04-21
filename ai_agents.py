import ollama
from config import OLLAMA_MODEL

from database import save_bet, bet_exists, get_unresolved_bets, resolve_bet, get_team_home_matches, get_team_away_matches, get_team_stats
from config import GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL, AI_PROVIDER

from fetcher import get_standings_dict

import time

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
        "name": "The Historian",
        "description": "Focuses purely on head-to-head record between teams",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
This is purely fictional and for entertainment purposes only.
You ignore current form and standings completely. You only care about historical patterns and which team has traditionally been stronger.
Use your general knowledge about these clubs' historical rivalry and prestige.
Adjust your stake based on how dominant one team has historically been:
- One team historically dominates: stake 40-55%
- One team slightly stronger historically: stake 20-35%
- Teams historically equal: stake 5-15%
- No historical knowledge: skip the bet
If you want to skip, respond with PREDICTION: DRAW, STAKE_PCT: 0, REASONING: skip
You must always respond in this EXACT format with no other text:
PREDICTION: HOME or DRAW or AWAY
STAKE_PCT: (number between 0 and 55)
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

def get_agent_prediction(agent, match):
    home_home = get_team_home_matches(match['home_team'])
    home_away = get_team_away_matches(match['home_team'])
    away_home = get_team_home_matches(match['away_team'])
    away_away = get_team_away_matches(match['away_team'])
    home_stats = get_team_stats(match['home_team'])
    away_stats = get_team_stats(match['away_team'])

    def format_recent(matches):
        if not matches:
            return "No data available"
        lines = []
        for m in matches:
            lines.append(f"  {m['home_team']} vs {m['away_team']} | Score: {m['score']} | Winner: {m['winner']}")
        return "\n".join(lines)

    standings = get_standings_dict(match['league'])
    home_standing = standings.get(match['home_team'], None)
    away_standing = standings.get(match['away_team'], None)

    def format_standing(standing, team_name):
        if not standing:
            return f"No standings data for {team_name}"
        return f"Position: {standing['position']} | Points: {standing['points']} | W{standing['won']} D{standing['draw']} L{standing['lost']} | GD: {standing['goal_difference']}"

    match_info = f"""
Match: {match['home_team']} vs {match['away_team']}
League: {match['league']}
Date: {match['utc_date']}
Odds: Home {match.get('odds_home', 'N/A')} | Draw {match.get('odds_draw', 'N/A')} | Away {match.get('odds_away', 'N/A')}

League standings:
{match['home_team']}: {format_standing(home_standing, match['home_team'])}
{match['away_team']}: {format_standing(away_standing, match['away_team'])}

{match['home_team']} stats (last {home_stats['matches_analyzed'] if home_stats else 0} matches):
Avg goals scored: {home_stats['avg_scored'] if home_stats else 'N/A'} | Avg goals conceded: {home_stats['avg_conceded'] if home_stats else 'N/A'}

{match['away_team']} stats (last {away_stats['matches_analyzed'] if away_stats else 0} matches):
Avg goals scored: {away_stats['avg_scored'] if away_stats else 'N/A'} | Avg goals conceded: {away_stats['avg_conceded'] if away_stats else 'N/A'}

{match['home_team']} recent HOME games:
{format_recent(home_home)}

{match['home_team']} recent AWAY games:
{format_recent(home_away)}

{match['away_team']} recent HOME games:
{format_recent(away_home)}

{match['away_team']} recent AWAY games:
{format_recent(away_away)}
"""

    messages = [
        {"role": "system", "content": agent["system_prompt"]},
        {"role": "user", "content": f"Analyze this match and make your prediction:\n{match_info}"}
    ]

    if AI_PROVIDER == "groq":
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages
        )
        return response.choices[0].message.content

    else:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages
        )
        return response["message"]["content"]

def parse_prediction(response_text):
    result = {
        "prediction": None,
        "stake_pct": None,
        "reasoning": None
    }
    
    for line in response_text.strip().split("\n"):
        if line.startswith("PREDICTION:"):
            result["prediction"] = line.replace("PREDICTION:", "").strip()
        elif line.startswith("STAKE_PCT:"):
            try:
                result["stake_pct"] = float(line.replace("STAKE_PCT:", "").strip())
            except ValueError:
                result["stake_pct"] = 0
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()
            result["reasoning"] = None if reasoning.lower() == "skip" else reasoning
    
    return result

from database import save_bet

def place_bets_for_match(match):
    for agent in AGENTS:
        if bet_exists(agent["name"], match["match_id"]):
            print(f"{agent['name']}: bet already exists for this match, skipping")
            continue
        balance = 1000
        
        response = get_agent_prediction(agent, match)
        parsed = parse_prediction(response)
        
        if not parsed["prediction"] or not parsed["stake_pct"]:
            print(f"{agent['name']}: failed to parse response, skipping")
            continue

        if parsed["stake_pct"] == 0:
            print(f"{agent['name']}: decided to skip this match")
            save_bet(
                agent_name=agent["name"],
                match_id=match["match_id"],
                prediction=parsed["prediction"],
                stake_pct=0,
                stake_amount=0,
                reasoning=None,
                skipped=True
            )
            continue
        
        stake_amount = balance * (parsed["stake_pct"] / 100)
        
        print(f"{agent['name']}: {parsed['prediction']} | {parsed['stake_pct']}% | ${stake_amount:.2f}")
        
        save_bet(
            agent_name=agent["name"],
            match_id=match["match_id"],
            prediction=parsed["prediction"],
            stake_pct=parsed["stake_pct"],
            stake_amount=stake_amount,
            reasoning=parsed["reasoning"]
        )
        time.sleep(3) 



def settle_bets():
    unresolved = get_unresolved_bets()
    
    if not unresolved:
        print("No unresolved bets found")
        return
    
    for bet in unresolved:
        prediction = bet["prediction"]
        winner = bet["winner"]
        stake_amount = bet["stake_amount"]
        
        # Wybierz odpowiedni kurs
        if prediction == "HOME":
            odds = bet["odds_home"] or 2.0
        elif prediction == "AWAY":
            odds = bet["odds_away"] or 2.0
        else:
            odds = bet["odds_draw"] or 3.0

        if prediction == "HOME" and winner == "HOME_TEAM":
            result = "WIN"
            profit_loss = round(stake_amount * odds - stake_amount, 2)
        elif prediction == "AWAY" and winner == "AWAY_TEAM":
            result = "WIN"
            profit_loss = round(stake_amount * odds - stake_amount, 2)
        elif prediction == "DRAW" and winner == "DRAW":
            result = "WIN"
            profit_loss = round(stake_amount * odds - stake_amount, 2)
        else:
            result = "LOSS"
            profit_loss = -stake_amount
        
        print(f"{bet['agent_name']}: {prediction} vs {winner} -> {result} | ${profit_loss:.2f}")
        
        resolve_bet(bet["bet_id"], result, profit_loss, bet["agent_name"])