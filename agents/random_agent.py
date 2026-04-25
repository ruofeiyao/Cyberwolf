# agents/random_agent.py
from __future__ import annotations
from typing import Dict, Any, List
import random
from agents.base import Agent

class RandomAgent(Agent):
    def __init__(self, agent_id: str, seed: int):
        super().__init__(agent_id)
        self.rng = random.Random(seed + hash(agent_id) % 10000)

    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        phase = obs["phase"]
        alive = [p for p, is_alive in obs["alive"].items() if is_alive]
        if phase == "DISCUSS":
            return {
                "reasoning": "I will say something generic.",
                "action": "SAY",
                "target": None,
                "utterance": "I am not sure yet. Let's see who is consistent."
            }
        # VOTE
        candidates = [p for p in alive if p != self.agent_id]
        target = self.rng.choice(candidates) if candidates else self.agent_id
        return {
            "reasoning": "Random vote baseline.",
            "action": "VOTE",
            "target": target,
            "utterance": ""
        }