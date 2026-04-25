from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
import csv

LOG_DIR = Path("logs")
OUT_CSV = Path("game_summary.csv")


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def summarize_game(rows: list[dict]) -> dict:
    if not rows:
        return {}

    game_id = rows[0].get("game_id", "")
    seed = rows[0].get("seed", "")

    max_round = 0
    winner = ""
    no_kill_nights = 0
    total_holds = 0
    seer_claimed = False
    doctor_publicly_identified = False
    first_elimination_role = ""
    first_elimination_round = ""
    first_elimination_player = ""

    role_map = {}
    alive_round1 = {}
    seer_player = None

    # track per-game notes
    turning_point_notes = []

    for row in rows:
        round_id = row.get("round_id")
        if isinstance(round_id, int):
            max_round = max(max_round, round_id)

        agent_id = row.get("agent_id")
        role_private = row.get("role_private")
        if agent_id and role_private:
            role_map[agent_id] = role_private
            if role_private == "SEER":
                seer_player = agent_id

        phase = row.get("phase", "")

        # round 1 alive snapshot
        obs = row.get("obs_public", {})
        if isinstance(obs, dict) and round_id == 1 and not alive_round1:
            alive_round1 = obs.get("alive", {}) or {}

        # count holds from action logs
        action = row.get("action")
        if isinstance(action, dict) and action.get("action") == "HOLD":
            total_holds += 1

        # detect claims in discussion utterances
        if phase == "DISCUSS" and isinstance(action, dict):
            utt = (action.get("utterance") or "").lower()
            if "i am the seer" in utt or "i'm the seer" in utt:
                seer_claimed = True
            if " is the doctor" in utt or "i am the doctor" in utt or "i'm the doctor" in utt:
                doctor_publicly_identified = True

        # resolve events
        event = row.get("event")
        if isinstance(event, dict):
            etype = event.get("type", "")
            payload = event.get("payload", {}) or {}

            if etype == "GAME_END":
                winner = payload.get("outcome", "")

            elif etype == "NO_NIGHT_KILL":
                no_kill_nights += 1
                if not turning_point_notes:
                    turning_point_notes.append("a no-kill night created ambiguity")

            elif etype == "ELIMINATED" and not first_elimination_role:
                first_elimination_role = payload.get("role", "")
                first_elimination_player = payload.get("player", "")
                first_elimination_round = round_id

    # Was seer alive after Night 1?
    seer_alive_round1 = ""
    if seer_player is not None and alive_round1:
        seer_alive_round1 = bool(alive_round1.get(seer_player, False))

    # crude turning point summary
    main_turning_point = "; ".join(turning_point_notes) if turning_point_notes else ""

    return {
        "game_id": game_id,
        "seed": seed,
        "winner": winner,
        "rounds": max_round,
        "seer_alive_round1": seer_alive_round1,
        "seer_claimed": seer_claimed,
        "doctor_publicly_identified": doctor_publicly_identified,
        "no_kill_nights": no_kill_nights,
        "total_holds": total_holds,
        "first_elimination_player": first_elimination_player,
        "first_elimination_role": first_elimination_role,
        "first_elimination_round": first_elimination_round,
        "main_turning_point": main_turning_point,
    }


def main():
    files = sorted(LOG_DIR.glob("*.jsonl"))
    if not files:
        print("No jsonl files found in logs/")
        return

    summaries = []
    for path in files:
        rows = load_jsonl(path)
        summary = summarize_game(rows)
        if summary:
            summaries.append(summary)

    if not summaries:
        print("No valid game summaries generated.")
        return

    fieldnames = [
        "game_id",
        "seed",
        "winner",
        "rounds",
        "seer_alive_round1",
        "seer_claimed",
        "doctor_publicly_identified",
        "no_kill_nights",
        "total_holds",
        "first_elimination_player",
        "first_elimination_role",
        "first_elimination_round",
        "main_turning_point",
    ]

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)

    print(f"Wrote {len(summaries)} game summaries to {OUT_CSV}")


if __name__ == "__main__":
    main()