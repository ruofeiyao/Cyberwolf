from __future__ import annotations
from typing import Any, Dict, Optional
import json
from schemas import ALLOWED_ACTIONS, ALLOWED_PLAYERS

def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse raw model output into a JSON object (dict).
    Returns None if parsing fails.
    """
    if not text:
        return None
    t = text.strip()

    # 1) direct parse
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # 2) extract first {...} block
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = t[start:end + 1]
        try:
            obj = json.loads(chunk)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    return None

def normalize_and_validate_action(obj: Dict[str, Any], phase: str) -> Optional[Dict[str, Any]]:
    """
    Enforce action schema + phase constraints.

    phase:
      - "DISCUSS": must return SAY with non-empty utterance
      - "VOTE": must return VOTE with valid target

    Returns a normalized dict:
      {"reasoning": str, "action": "SAY|VOTE", "target": str|None, "utterance": str}
    """
    if not isinstance(obj, dict):
        return None

    reasoning = obj.get("reasoning", "")
    action = obj.get("action")
    target = obj.get("target", None)
    utterance = obj.get("utterance", "")

    # normalize fields
    if reasoning is None:
        reasoning = ""
    if utterance is None:
        utterance = ""
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)
    if not isinstance(utterance, str):
        utterance = str(utterance)

    # force action by phase (prevents invalid runs)
    if phase == "VOTE":
        action = "VOTE"
    elif phase == "DISCUSS":
        action = "SAY"

    if action not in ALLOWED_ACTIONS:
        return None

    if action == "VOTE":
        if target not in ALLOWED_PLAYERS:
            return None
        return {
            "reasoning": reasoning.strip(),
            "action": "VOTE",
            "target": target,
            "utterance": ""
        }

    # SAY
    if len(utterance.strip()) == 0:
        return None
    return {
        "reasoning": reasoning.strip(),
        "action": "SAY",
        "target": None,
        "utterance": utterance.strip()
    }