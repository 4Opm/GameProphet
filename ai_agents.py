import ollama
from config import OLLAMA_MODEL

from database import save_bet, get_agent_balance, get_team_recent_matches, bet_exists, get_unresolved_bets, resolve_bet



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
        REASONING: (one sentence explanation)"""
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
        REASONING: (one sentence explanation)"""
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
        REASONING: (one sentence explanation)"""
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
        REASONING: (one sentence explanation)"""
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
        REASONING: (one sentence explanation)"""
    }
]


def get_agent_prediction(agent, match):
    home_recent = get_team_recent_matches(match['home_team'])
    away_recent = get_team_recent_matches(match['away_team'])

    def format_recent(matches, team_name):
        if not matches:
            return f"No recent matches found for {team_name}"
        lines = []
        for m in matches:
            lines.append(f"  {m['home_team']} vs {m['away_team']} | Score: {m['score']} | Winner: {m['winner']}")
        return "\n".join(lines)

    match_info = f"""
Match: {match['home_team']} vs {match['away_team']}
League: {match['league']}
Date: {match['utc_date']}

Recent form of {match['home_team']}:
{format_recent(home_recent, match['home_team'])}

Recent form of {match['away_team']}:
{format_recent(away_recent, match['away_team'])}
"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": f"Analyze this match and make your prediction:\n{match_info}"}
        ]
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
        balance = get_agent_balance(agent["name"])
        
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



def settle_bets():
    unresolved = get_unresolved_bets()
    
    if not unresolved:
        print("No unresolved bets found")
        return
    
    for bet in unresolved:
        prediction = bet["prediction"]
        winner = bet["winner"]
        stake_amount = bet["stake_amount"]
        
        if prediction == "HOME" and winner == "HOME_TEAM":
            result = "WIN"
            profit_loss = stake_amount
        elif prediction == "AWAY" and winner == "AWAY_TEAM":
            result = "WIN"
            profit_loss = stake_amount
        elif prediction == "DRAW" and winner == "DRAW":
            result = "WIN"
            profit_loss = stake_amount
        else:
            result = "LOSS"
            profit_loss = -stake_amount
        
        print(f"{bet['agent_name']}: {prediction} vs {winner} -> {result} | ${profit_loss:.2f}")
        
        resolve_bet(bet["bet_id"], result, profit_loss, bet["agent_name"])