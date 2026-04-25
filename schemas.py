from __future__ import annotations
from typing import Any, Dict, Optional, Literal, TypedDict, List

ActionType = Literal["SAY", "VOTE", "HOLD", "KILL", "INVESTIGATE", "PROTECT"]
PlayerId = Literal["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]

class Action(TypedDict, total=False):
    reasoning: str
    action: ActionType
    target: Optional[PlayerId]
    utterance: str

ACTION_SCHEMA_HINT: Dict[str, Any] = {
    "reasoning": "string (brief, in English)",
    "action": "SAY | VOTE | HOLD | KILL | INVESTIGATE | PROTECT",
    "target": "P0|P1|P2|P3|P4|P5|P6|P7|null (required for VOTE, KILL, INVESTIGATE, PROTECT; otherwise null)",
    "utterance": "string (required if action=SAY, otherwise empty string)"
}

ALLOWED_ACTIONS: List[str] = ["SAY", "VOTE", "HOLD", "KILL", "INVESTIGATE", "PROTECT"]
ALLOWED_PLAYERS: List[str] = [f"P{i}" for i in range(8)]