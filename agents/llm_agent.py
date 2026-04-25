from __future__ import annotations
from typing import Dict, Any, Optional
import json
import time

from google import genai
from google.genai.types import HttpOptions

from agents.base import Agent
from prompts import build_prompt

PROJECT_ID = "bold-passkey-418620"
LOCATION = "us-central1"


def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


class LlmAgent(Agent):
    def __init__(
        self,
        agent_id: str,
        model: str,
        role: str,
        temperature: float = 0.3,
        top_p: float = 0.9,
        max_tokens: int = 400,
        memory_on: bool = False,
        reflection_on: bool = False,
        prompt_style: str = "strategic",
    ):
        super().__init__(agent_id)
        self.model = model
        self.role = role
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.memory_on = memory_on
        self.reflection_on = reflection_on
        self.memory: list[str] = []
        self.prompt_style = prompt_style

        self.client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
            http_options=HttpOptions(api_version="v1"),
        )

    def _memory_block(self, obs: Dict[str, Any]) -> Optional[str]:
        if not self.memory_on:
            return None

        last_votes = obs.get("last_votes", {})
        last_holds = obs.get("last_holds", [])
        private_events = obs.get("private_events", [])
        notes = self.memory[-8:]

        return (
            f"Recent vote record: {last_votes}\n"
            f"Recent holds: {last_holds}\n"
            f"Persistent private events: {private_events}\n"
            f"Memory notes: {notes}"
        )

    def _call_model(self, prompt: str) -> str:
        max_retries = 3
        backoff_seconds = 3

        for attempt in range(max_retries):
            try:
                print(f"[CALL] {self.agent_id} phase request start (attempt {attempt + 1}/{max_retries})")

                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )

                text = resp.text if resp.text is not None else ""
                print(f"[CALL] {self.agent_id} response received")
                return text

            except Exception as e:
                print(f"[WARN] Model call failed for {self.agent_id}: {e}")

                if attempt < max_retries - 1:
                    sleep_time = backoff_seconds * (attempt + 1)
                    print(f"[WARN] Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    raise

    def _fallback(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        phase = obs["phase"]

        if phase == "NIGHT":
            role = self.role

            if role == "WOLF":
                wolf_teammates = set(obs.get("wolf_teammates", []))
                alive_targets = [
                    p for p, ok in obs["alive"].items()
                    if ok and p != self.agent_id and p not in wolf_teammates
                ]
                target = sorted(alive_targets)[0] if alive_targets else None
                return {
                    "reasoning": "Fallback: selecting a valid wolf night target.",
                    "action": "KILL",
                    "target": target,
                    "utterance": ""
                }

            if role == "SEER":
                alive_targets = [
                    p for p, ok in obs["alive"].items()
                    if ok and p != self.agent_id
                ]
                target = sorted(alive_targets)[0] if alive_targets else None
                return {
                    "reasoning": "Fallback: selecting a valid investigate target.",
                    "action": "INVESTIGATE",
                    "target": target,
                    "utterance": ""
                }

            if role == "DOCTOR":
                valid_targets = [p for p, ok in obs["alive"].items() if ok]
                target = sorted(valid_targets)[0] if valid_targets else self.agent_id
                return {
                    "reasoning": "Fallback: selecting a valid protect target.",
                    "action": "PROTECT",
                    "target": target,
                    "utterance": ""
                }

            return {
                "reasoning": "I have no night action.",
                "action": "HOLD",
                "target": None,
                "utterance": ""
            }

        if phase == "VOTE":
            return {
                "reasoning": "Fallback: there is not enough confidence to cast a justified vote.",
                "action": "HOLD",
                "target": None,
                "utterance": ""
            }

        return {
            "reasoning": "Fallback discussion move.",
            "action": "SAY",
            "target": None,
            "utterance": "I want to hear more before making a decision."
        }

    def _postprocess(self, parsed: Dict[str, Any], obs: Dict[str, Any]) -> Dict[str, Any]:
        action = parsed.get("action")
        reasoning = parsed.get("reasoning", "")
        target = parsed.get("target", None)
        utterance = parsed.get("utterance", "")

        if not isinstance(reasoning, str):
            reasoning = str(reasoning)
        if not isinstance(utterance, str):
            utterance = str(utterance)

        phase = obs["phase"]

        if phase == "NIGHT":
            role = self.role

            if role == "WOLF":
                wolf_teammates = set(obs.get("wolf_teammates", []))
                alive_targets = [
                    p for p, ok in obs["alive"].items()
                    if ok and p != self.agent_id and p not in wolf_teammates
                ]
                if action not in ["KILL", "HOLD"]:
                    return self._fallback(obs)
                if action == "HOLD":
                    return {
                        "reasoning": reasoning.strip() or "The current night situation does not justify a kill target yet.",
                        "action": "HOLD",
                        "target": None,
                        "utterance": ""
                    }
                if target not in alive_targets:
                    return self._fallback(obs)
                return {
                    "reasoning": reasoning.strip() or "I am selecting a strategically useful night target.",
                    "action": "KILL",
                    "target": target,
                    "utterance": ""
                }

            if role == "SEER":
                alive_targets = [
                    p for p, ok in obs["alive"].items()
                    if ok and p != self.agent_id
                ]
                if action not in ["INVESTIGATE", "HOLD"]:
                    return self._fallback(obs)
                if action == "HOLD":
                    return {
                        "reasoning": reasoning.strip() or "I will hold my night investigation for now.",
                        "action": "HOLD",
                        "target": None,
                        "utterance": ""
                    }
                if target not in alive_targets:
                    return self._fallback(obs)
                return {
                    "reasoning": reasoning.strip() or "I am selecting a target to investigate.",
                    "action": "INVESTIGATE",
                    "target": target,
                    "utterance": ""
                }

            if role == "DOCTOR":
                valid_targets = [p for p, ok in obs["alive"].items() if ok]
                if action not in ["PROTECT", "HOLD"]:
                    return self._fallback(obs)
                if action == "HOLD":
                    return {
                        "reasoning": reasoning.strip() or "I will hold my protection for this night.",
                        "action": "HOLD",
                        "target": None,
                        "utterance": ""
                    }
                if target not in valid_targets:
                    return self._fallback(obs)
                return {
                    "reasoning": reasoning.strip() or "I am selecting a target to protect.",
                    "action": "PROTECT",
                    "target": target,
                    "utterance": ""
                }

            return {
                "reasoning": "I have no night action.",
                "action": "HOLD",
                "target": None,
                "utterance": ""
            }

        if phase == "DISCUSS":
            utterance = utterance.strip()
            if not utterance:
                utterance = "I want to hear more before making a decision."
            return {
                "reasoning": reasoning.strip() or "I am gathering more information from the discussion.",
                "action": "SAY",
                "target": None,
                "utterance": utterance
            }

        # VOTE
        if action not in ["VOTE", "HOLD"]:
            action = "HOLD"

        if action == "HOLD":
            return {
                "reasoning": reasoning.strip() or "There is not enough evidence to justify a vote yet.",
                "action": "HOLD",
                "target": None,
                "utterance": ""
            }

        alive = [p for p, ok in obs["alive"].items() if ok and p != self.agent_id]
        if target not in alive:
            return {
                "reasoning": reasoning.strip() or "There is not enough reliable evidence to support a specific vote.",
                "action": "HOLD",
                "target": None,
                "utterance": ""
            }

        return {
            "reasoning": reasoning.strip() or "I am selecting the most plausible target based on the current state.",
            "action": "VOTE",
            "target": target,
            "utterance": ""
        }

    def act(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        prompt = build_prompt(
            agent_id=self.agent_id,
            role=self.role,
            obs=obs,
            instruction=None,
            memory_block=self._memory_block(obs),
            prompt_style=self.prompt_style,
        )

        try:
            raw = self._call_model(prompt)
            parsed = _safe_json_parse(raw)

            if not parsed:
                print(f"[WARN] Invalid JSON from model for {self.agent_id} in phase {obs['phase']}. Using fallback.")
                action = self._fallback(obs)
            else:
                action = self._postprocess(parsed, obs)

        except Exception as e:
            print(f"[WARN] Model call crashed for {self.agent_id} in phase {obs['phase']}: {e}")
            action = self._fallback(obs)

        if self.reflection_on:
            phase = obs["phase"]
            if phase == "VOTE":
                if action["action"] == "VOTE":
                    self.memory.append(
                        f"I voted {action.get('target')}. I should track whether this vote was justified."
                    )
                elif action["action"] == "HOLD":
                    self.memory.append(
                        "I chose HOLD because the evidence was not strong enough."
                    )
            elif phase == "NIGHT":
                self.memory.append(
                    f"In the night phase, I chose {action.get('action')} targeting {action.get('target')}."
                )

        return action