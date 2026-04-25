import uuid
import time
import argparse
from engine import WerewolfEngine
from agents.llm_agent import LlmAgent
from logging_utils import JsonlLogger
PROMPT_STYLE = "strategic"

parser = argparse.ArgumentParser()
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--prompt_style", type=str, default="strategic")
args = parser.parse_args()

seed = args.seed

def main():
    seed = args.seed
    game_id = str(uuid.uuid4())[:8]

    engine = WerewolfEngine(n_players=8, vote_threshold=3)
    state = engine.reset(seed=seed, game_id=game_id)

    model_name = "gemini-2.5-flash"

    agents = {}
    for p in state.players:
        agents[p] = LlmAgent(
            agent_id=p,
            model=model_name,
            role=state.roles[p],
            temperature=0.3,
            memory_on=True,
            reflection_on=False,
            prompt_style=args.prompt_style
        )
    logger = JsonlLogger(f"logs/{args.prompt_style}_{game_id}.jsonl")

    done = False
    outcome = None
    previous_vote_events = None

    print(f"Demo game_id={game_id}, seed={seed}, model={model_name}, prompt_style={args.prompt_style}")

    while not done and state.round_id <= 10:
        # ===== NIGHT =====
        engine.start_night(state, previous_vote_events)
        print(f"\n=== NIGHT {state.round_id} ===")

        night_obs_public = engine.get_public_observation(state)
        for e in night_obs_public.get("public_events", []):
            print(f"PUBLIC EVENT: {e}")

        for p in state.players:
            if not state.alive[p]:
                continue

            role = state.roles[p]
            if role not in ["WOLF", "SEER", "DOCTOR"]:
                continue

            agent_obs = engine.get_agent_observation(state, p)
            action = agents[p].act(agent_obs | {"phase": "NIGHT"})
            time.sleep(1)

            engine.record_night_action(state, p, action.get("action"), action.get("target"))

            logger.log({
                "game_id": game_id,
                "seed": seed,
                "round_id": state.round_id,
                "phase": "NIGHT",
                "agent_id": p,
                "role_private": role,
                "obs_public": agent_obs,
                "action": action
            })

            print(f"[R{state.round_id} NIGHT] {p} ({role}) -> {action.get('action')} {action.get('target')}")
            print(f"    reasoning: {action.get('reasoning', '')}")

        night_events = engine.resolve_night(state)
        for ev in night_events:
            logger.log({
                "game_id": game_id,
                "seed": seed,
                "round_id": state.round_id,
                "phase": "NIGHT_RESOLVE",
                "event": {"type": ev.type, "payload": ev.payload}
            })
            print(f"EVENT: {ev.type} {ev.payload}")
            if ev.type == "GAME_END":
                done = True
                outcome = ev.payload["outcome"]

        if done:
            break

        # ===== DAY START / DISCUSS =====
        engine.start_day(state, night_events, previous_vote_events)
        day_obs_public = engine.get_public_observation(state)

        print(f"\n=== DAY {state.round_id} START ===")
        for e in day_obs_public.get("public_events", []):
            print(f"PUBLIC EVENT: {e}")

        for p in state.players:
            if not state.alive[p]:
                continue

            agent_obs = engine.get_agent_observation(state, p)
            action = agents[p].act(agent_obs | {"phase": "DISCUSS"})
            time.sleep(1)
            engine.apply_say(state, p, action.get("utterance", ""))

            logger.log({
                "game_id": game_id,
                "seed": seed,
                "round_id": state.round_id,
                "phase": "DISCUSS",
                "agent_id": p,
                "role_private": state.roles[p],
                "obs_public": agent_obs,
                "action": action
            })

            print(f"[R{state.round_id} DISCUSS] {p}: {action.get('utterance', '')}")
            print(f"    reasoning: {action.get('reasoning', '')}")

        # ===== VOTE =====
        engine.move_to_vote_phase(state)

        for p in state.players:
            if not state.alive[p]:
                continue

            agent_obs = engine.get_agent_observation(state, p)
            action = agents[p].act(agent_obs | {"phase": "VOTE"})
            time.sleep(1)

            if action.get("action") == "VOTE":
                engine.apply_vote(state, p, action.get("target"))
                print(f"[R{state.round_id} VOTE] {p} -> {action.get('target')}")
            else:
                engine.apply_hold(state, p)
                print(f"[R{state.round_id} VOTE] {p} -> HOLD")

            print(f"    reasoning: {action.get('reasoning', '')}")

            logger.log({
                "game_id": game_id,
                "seed": seed,
                "round_id": state.round_id,
                "phase": "VOTE",
                "agent_id": p,
                "role_private": state.roles[p],
                "obs_public": agent_obs,
                "action": action
            })

        vote_events = engine.resolve_votes(state)
        for ev in vote_events:
            logger.log({
                "game_id": game_id,
                "seed": seed,
                "round_id": state.round_id,
                "phase": "VOTE_RESOLVE",
                "event": {"type": ev.type, "payload": ev.payload}
            })
            print(f"EVENT: {ev.type} {ev.payload}")
            if ev.type == "GAME_END":
                done = True
                outcome = ev.payload["outcome"]

        if done:
            break

        previous_vote_events = vote_events
        state.round_id += 1

    print("DONE:", outcome)


if __name__ == "__main__":
    main()