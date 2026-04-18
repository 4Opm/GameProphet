import ollama
from config import OLLAMA_MODEL

from database import save_bet, get_agent_balance, get_team_recent_matches, bet_exists, get_unresolved_bets, resolve_bet, get_team_home_matches, get_team_away_matches, get_team_stats
from config import GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL, AI_PROVIDER

from fetcher import fetch_matches, get_standings_dict

import time

AGENTS = [
    {
        "name": "Conservative Carl",
        "description": "Bets only on clear favorites, small stakes",
        "strategy": "conservative",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You are very conservative and only bet when you are highly confident. Analyze league standings, recent form, home/away performance, goals scored/conceded and odds carefully.
        If you are not confident enough, set STAKE_PCT to 0 to skip the bet.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 0 and 60)
        REASONING: (two sentence analysis based on the provided data)
        """
    },
    {
        "name": "Aggressive Alex",
        "description": "High risk, high reward, bets big on gut feeling",
        "strategy": "aggressive",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You love high risk predictions and always go big. Analyze league standings, recent form, home/away performance, goals scored/conceded and odds carefully before betting large amounts.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 20 and 100)
        REASONING: (two sentence analysis based on the provided data)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
    },
    {
        "name": "Statistical Steve",
        "description": "Analyzes stats and form, medium stakes",
        "strategy": "statistical",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You are a data-driven analyst. Always base your prediction strictly on league standings, recent form, home/away records, average goals scored/conceded and betting odds.
        If the data is inconclusive, set STAKE_PCT to 0 to skip the bet.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 0 and 60)
        REASONING: (two sentence analysis based on the provided data)
        """
    },
    {
        "name": "Form Fred",
        "description": "Focuses only on recent team form",
        "strategy": "form_based",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You focus purely on recent team momentum and form. Analyze the last home and away games carefully, looking for winning streaks, scoring runs and defensive solidity.
        If recent form is unclear, set STAKE_PCT to 0 to skip the bet.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 0 and 60)
        REASONING: (two sentence analysis based on the provided data)
        """
    },
    {
        "name": "Random Randy",
        "description": "Completely random strategy, baseline agent",
        "strategy": "random",
        "system_prompt": """You are a chaotic fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You make completely unpredictable random decisions with no logic whatsoever. Sometimes you bet big, sometimes nothing.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 1 and 100)
        REASONING: (one completely random and absurd sentence)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
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
            result["stake_pct"] = float(line.replace("STAKE_PCT:", "").strip())
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.replace("REASONING:", "").strip()
    
    return result

from database import save_bet, get_agent_balance

def place_bets_for_match(match):
    for agent in AGENTS:
        if bet_exists(agent["name"], match["match_id"]):
            print(f"{agent['name']}: bet already exists for this match, skipping")
            continue
        balance = 10000
        
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
                reasoning=parsed["reasoning"],
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