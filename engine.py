from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any
import random

Role = str  # "WOLF" | "SEER" | "DOCTOR" | "VILLAGER"


@dataclass
class Turn:
    round_id: int
    phase: str
    agent_id: str
    content: str


@dataclass
class StepEvent:
    type: str
    payload: Dict[str, Any]


@dataclass
class GameState:
    game_id: str
    seed: int
    round_id: int
    phase: str  # "NIGHT" | "DISCUSS" | "VOTE"
    players: List[str]
    alive: Dict[str, bool]
    roles: Dict[str, Role]

    public_history: List[Turn]
    public_events: List[str]

    last_votes: Dict[str, str]
    last_holds: List[str]
    vote_threshold: int

    # Night action buffers
    wolf_kills: Dict[str, str] = field(default_factory=dict)   # wolf_id -> target
    doctor_protect: Optional[str] = None
    seer_investigate: Optional[str] = None

    # Persistent private memory/events for each player
    private_events: Dict[str, List[str]] = field(default_factory=dict)


class WerewolfEngine:
    def __init__(self, n_players: int = 8, vote_threshold: int = 3):
        assert n_players == 8, "This version assumes 8 players."
        self.n_players = n_players
        self.vote_threshold = vote_threshold

    def reset(self, seed: int, game_id: str) -> GameState:
        rng = random.Random(seed)
        players = [f"P{i}" for i in range(self.n_players)]

        # 8-player setup: 2 wolves, 1 seer, 1 doctor, 4 villagers
        role_list = ["WOLF", "WOLF", "SEER", "DOCTOR", "VILLAGER", "VILLAGER", "VILLAGER", "VILLAGER"]
        rng.shuffle(role_list)
        roles = {p: role_list[i] for i, p in enumerate(players)}

        alive = {p: True for p in players}
        private_events = {p: [] for p in players}

        state = GameState(
            game_id=game_id,
            seed=seed,
            round_id=1,
            phase="NIGHT",
            players=players,
            alive=alive,
            roles=roles,
            public_history=[],
            public_events=["Night 1 begins.", "There is no prior vote history yet."],
            last_votes={},
            last_holds=[],
            vote_threshold=self.vote_threshold,
            private_events=private_events
        )
        return state

    # ---------- observations ----------
    def get_public_observation(self, state: GameState) -> Dict[str, Any]:
        return {
            "game_id": state.game_id,
            "seed": state.seed,
            "round_id": state.round_id,
            "phase": state.phase,
            "players": state.players,
            "alive": dict(state.alive),
            "public_events": list(state.public_events),
            "public_history": [asdict(t) for t in state.public_history[-40:]],
            "last_votes": dict(state.last_votes),
            "last_holds": list(state.last_holds),
            "vote_threshold": state.vote_threshold,
        }

    def get_agent_observation(self, state: GameState, agent_id: str) -> Dict[str, Any]:
        obs = self.get_public_observation(state)
        obs["private_role"] = state.roles[agent_id]
        obs["private_events"] = list(state.private_events.get(agent_id, []))

        if state.roles[agent_id] == "WOLF":
            alive_wolves = [p for p in state.players if state.alive[p] and state.roles[p] == "WOLF"]
            obs["wolf_teammates"] = [p for p in alive_wolves if p != agent_id]

        return obs

    # ---------- terminal ----------
    def is_terminal(self, state: GameState) -> Tuple[bool, Optional[str]]:
        alive_players = [p for p in state.players if state.alive[p]]
        alive_wolves = [p for p in alive_players if state.roles[p] == "WOLF"]
        alive_nonwolves = [p for p in alive_players if state.roles[p] != "WOLF"]

        if len(alive_wolves) == 0:
            return True, "VILLAGERS_WIN"
        if len(alive_wolves) >= len(alive_nonwolves):
            return True, "WOLVES_WIN"
        return False, None

    # ---------- helpers ----------
    def get_alive_wolves(self, state: GameState) -> List[str]:
        return [p for p in state.players if state.alive[p] and state.roles[p] == "WOLF"]

    def get_alive_specials(self, state: GameState) -> List[str]:
        return [p for p in state.players if state.alive[p] and state.roles[p] in {"SEER", "DOCTOR"}]

    # ---------- phase transitions ----------
    def start_night(self, state: GameState, previous_vote_events: Optional[List[StepEvent]]) -> None:
        state.phase = "NIGHT"
        state.public_events = [f"Night {state.round_id} begins."]

        if previous_vote_events is None:
            state.public_events.append("There is no prior vote history yet.")
        else:
            for ev in previous_vote_events:
                if ev.type == "VOTE_RESULT":
                    state.public_events.append(f"Previous vote counts: {ev.payload.get('counts', {})}.")
                    state.public_events.append(f"Previous holds: {ev.payload.get('holds', [])}.")
                elif ev.type == "ELIMINATED":
                    state.public_events.append(f"{ev.payload['player']} was eliminated by vote in the previous day.")
                elif ev.type == "NO_ELIMINATION":
                    state.public_events.append(ev.payload["reason"])

        state.wolf_kills = {}
        state.doctor_protect = None
        state.seer_investigate = None

    def start_day(
        self,
        state: GameState,
        night_events: List[StepEvent],
        previous_vote_events: Optional[List[StepEvent]],
    ) -> None:
        state.phase = "DISCUSS"
        state.public_events = [f"Day {state.round_id} begins."]

        alive_players = [p for p in state.players if state.alive[p]]
        state.public_events.append(f"Alive players: {', '.join(alive_players)}.")

        # Carry over previous day vote results into this day's shared knowledge
        if previous_vote_events is None:
            state.public_events.append("There is no prior vote history yet.")
        else:
            for ev in previous_vote_events:
                if ev.type == "VOTE_RESULT":
                    state.public_events.append(f"Previous vote counts: {ev.payload.get('counts', {})}.")
                    state.public_events.append(f"Previous holds: {ev.payload.get('holds', [])}.")
                elif ev.type == "ELIMINATED":
                    state.public_events.append(f"{ev.payload['player']} was eliminated by vote in the previous day.")
                elif ev.type == "NO_ELIMINATION":
                    state.public_events.append(ev.payload["reason"])

        # Then append night results
        if night_events:
            for ev in night_events:
                if ev.type == "NIGHT_KILL":
                    state.public_events.append(f"{ev.payload['player']} was killed during the night.")
                elif ev.type == "NO_NIGHT_KILL":
                    state.public_events.append(ev.payload.get("reason", "No one died during the night."))
        else:
            state.public_events.append("No one died during the night.")

        state.last_votes = {}
        state.last_holds = []

    def move_to_vote_phase(self, state: GameState) -> None:
        state.phase = "VOTE"

    # ---------- night actions ----------
    def record_night_action(self, state: GameState, agent_id: str, action: str, target: Optional[str]) -> None:
        if not state.alive.get(agent_id, False):
            return

        role = state.roles[agent_id]

        if role == "WOLF" and action == "KILL" and target is not None:
            if state.alive.get(target, False) and state.roles[target] != "WOLF":
                state.wolf_kills[agent_id] = target

        elif role == "DOCTOR" and action == "PROTECT" and target is not None:
            if state.alive.get(target, False):
                state.doctor_protect = target

        elif role == "SEER" and action == "INVESTIGATE" and target is not None:
            if state.alive.get(target, False) and target != agent_id:
                state.seer_investigate = target

    def resolve_night(self, state: GameState) -> List[StepEvent]:
        events: List[StepEvent] = []

        # Seer result goes into persistent private memory
        if state.seer_investigate is not None:
            target = state.seer_investigate
            role = state.roles[target]
            seers = [p for p in state.players if state.alive[p] and state.roles[p] == "SEER"]
            for seer_id in seers:
                state.private_events[seer_id].append(
                    f"You investigated {target}. Their role is {role}."
                )

        # Resolve wolves' kill by majority / deterministic tie-break
        if state.wolf_kills:
            counts: Dict[str, int] = {}
            for _, target in state.wolf_kills.items():
                counts[target] = counts.get(target, 0) + 1

            max_count = max(counts.values())
            candidates = [p for p, c in counts.items() if c == max_count]
            kill_target = sorted(candidates)[0]

            if state.doctor_protect == kill_target:
                events.append(
                    StepEvent(
                        type="NO_NIGHT_KILL",
                        payload={"reason": "No one died during the night."}
                    )
                )
            else:
                if state.alive.get(kill_target, False):
                    state.alive[kill_target] = False
                    events.append(StepEvent(type="NIGHT_KILL", payload={"player": kill_target}))
        else:
            events.append(
                StepEvent(
                    type="NO_NIGHT_KILL",
                    payload={"reason": "No one died during the night."}
                )
            )

        done, outcome = self.is_terminal(state)
        if done:
            events.append(StepEvent(type="GAME_END", payload={"outcome": outcome}))

        return events

    # ---------- discuss ----------
    def apply_say(self, state: GameState, agent_id: str, utterance: str) -> None:
        state.public_history.append(
            Turn(round_id=state.round_id, phase="DISCUSS", agent_id=agent_id, content=utterance)
        )

    # ---------- voting ----------
    def apply_vote(self, state: GameState, agent_id: str, target: str) -> None:
        state.last_votes[agent_id] = target

    def apply_hold(self, state: GameState, agent_id: str) -> None:
        if agent_id not in state.last_holds:
            state.last_holds.append(agent_id)

    def resolve_votes(self, state: GameState) -> List[StepEvent]:
        vote_counts: Dict[str, int] = {}

        for voter, target in state.last_votes.items():
            if not state.alive.get(voter, False):
                continue
            if not state.alive.get(target, False):
                continue
            vote_counts[target] = vote_counts.get(target, 0) + 1

        events: List[StepEvent] = [
            StepEvent(
                type="VOTE_RESULT",
                payload={
                    "counts": vote_counts,
                    "holds": list(state.last_holds),
                    "threshold": state.vote_threshold
                }
            )
        ]

        if not vote_counts:
            events.append(StepEvent(type="NO_ELIMINATION", payload={"reason": "No votes were cast."}))
            return events

        max_votes = max(vote_counts.values())
        top = [t for t, c in vote_counts.items() if c == max_votes]
        eliminated = sorted(top)[0]

        if max_votes < state.vote_threshold:
            events.append(
                StepEvent(
                    type="NO_ELIMINATION",
                    payload={
                        "reason": f"No player reached the elimination threshold of {state.vote_threshold} votes.",
                        "top_candidates": top,
                        "max_votes": max_votes
                    }
                )
            )
            return events

        state.alive[eliminated] = False
        events.append(
            StepEvent(
                type="ELIMINATED",
                payload={"player": eliminated, "role": state.roles[eliminated]}
            )
        )

        done, outcome = self.is_terminal(state)
        if done:
            events.append(StepEvent(type="GAME_END", payload={"outcome": outcome}))

        return events