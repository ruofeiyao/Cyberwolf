# agents/base.py
from __future__ import annotations
from typing import Dict, Any

class Agent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Must return an action dict:
        {
          "reasoning": str,
          "action": "SAY" or "VOTE",
          "target": "P0".."P4" or None,
          "utterance": str
        }
        """
        raise NotImplementedError