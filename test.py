from database import get_upcoming_matches
from ai_agents import AGENTS, get_agent_prediction, parse_prediction

matches = get_upcoming_matches()
match = matches[0]

response = get_agent_prediction(AGENTS[0], match)
print(response)