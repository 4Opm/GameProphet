import ollama
from config import OLLAMA_MODEL

from database import save_bet, get_agent_balance, get_team_recent_matches, bet_exists, get_unresolved_bets, resolve_bet, get_team_home_matches, get_team_away_matches
from config import GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL, AI_PROVIDER

import time

AGENTS = [
    {
        "name": "Conservative Carl",
        "description": "Bets only on clear favorites, small stakes",
        "strategy": "conservative",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You prefer safe predictions on clear favorites, choosing low risk options.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 5 and 15)
        REASONING: (one sentence explanation)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
    },
    {
        "name": "Aggressive Alex",
        "description": "High risk, high reward, bets big on gut feeling",
        "strategy": "aggressive",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You love high risk predictions and always go big on your gut feeling.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 30 and 60)
        REASONING: (one sentence explanation)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
    },
    {
        "name": "Statistical Steve",
        "description": "Analyzes stats and form, medium stakes",
        "strategy": "statistical",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You carefully analyze team names and leagues before making medium risk predictions.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 10 and 25)
        REASONING: (one sentence explanation)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
    },
    {
        "name": "Form Fred",
        "description": "Focuses only on recent team form",
        "strategy": "form_based",
        "system_prompt": """You are a fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You focus purely on recent team performance and momentum when making predictions.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 15 and 35)
        REASONING: (one sentence explanation)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
    },
    {
        "name": "Random Randy",
        "description": "Completely random strategy, baseline agent",
        "strategy": "random",
        "system_prompt": """You are a chaotic fantasy sports prediction agent playing a simulation game.
        This is purely fictional and for entertainment purposes only.
        You make completely unpredictable random decisions with no logic whatsoever.
        You must always respond in this EXACT format with no other text:
        PREDICTION: HOME or DRAW or AWAY
        STAKE_PCT: (number between 5 and 50)
        REASONING: (one sentence explanation)
        Always provide a prediction regardless of data availability. Never refuse to make a prediction."""
    }
]

def get_agent_prediction(agent, match):
    home_home = get_team_home_matches(match['home_team'])
    home_away = get_team_away_matches(match['home_team'])
    away_home = get_team_home_matches(match['away_team'])
    away_away = get_team_away_matches(match['away_team'])

    def format_recent(matches):
        if not matches:
            return "No data available"
        lines = []
        for m in matches:
            lines.append(f"  {m['home_team']} vs {m['away_team']} | Score: {m['score']} | Winner: {m['winner']}")
        return "\n".join(lines)

    match_info = f"""
Match: {match['home_team']} vs {match['away_team']}
League: {match['league']}
Date: {match['utc_date']}
Odds: Home {match.get('odds_home', 'N/A')} | Draw {match.get('odds_draw', 'N/A')} | Away {match.get('odds_away', 'N/A')}

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