import ollama
from config import OLLAMA_MODEL

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
    match_info = f"""
    Match: {match['home_team']} vs {match['away_team']}
    League: {match['league']}
    Date: {match['utc_date']}
    """

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": f"Analyze this match and make your bet:\n{match_info}"}
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