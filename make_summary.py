import os
import json
import csv

LOG_DIR = "logs"
OUT_CSV = "game_summary_labeled.csv"

def process_file(path, prompt_style):
    with open(path, encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]

    if not lines:
        return None

    seed = None
    game_id = None
    rounds = 0
    winner = None

    holds = 0
    no_kill_nights = 0
    seer_claimed = False
    doctor_identified = False
    first_elim = None

    for l in lines:
        seed = l.get("seed", seed)
        game_id = l.get("game_id", game_id)

        phase = l.get("phase", "")

        if phase == "VOTE":
            if l.get("action", {}).get("action") == "HOLD":
                holds += 1

        if phase == "DISCUSS":
            utt = l.get("action", {}).get("utterance", "").lower()
            if "i am the seer" in utt or "i'm the seer" in utt:
                seer_claimed = True
            if "i am the doctor" in utt or "i'm the doctor" in utt:
                doctor_identified = True

        if phase == "NIGHT_RESOLVE":
            ev = l.get("event", {})
            if ev.get("type") == "NO_NIGHT_KILL":
                no_kill_nights += 1
            if ev.get("type") == "GAME_END":
                winner = ev.get("payload", {}).get("outcome")

        if phase == "VOTE_RESOLVE":
            rounds = max(rounds, l.get("round_id", 0))
            ev = l.get("event", {})
            if ev.get("type") == "ELIMINATED" and first_elim is None:
                first_elim = ev.get("payload", {})
            if ev.get("type") == "GAME_END":
                winner = ev.get("payload", {}).get("outcome")

    return {
        "game_id": game_id,
        "seed": seed,
        "prompt_style": prompt_style,
        "winner": winner,
        "rounds": rounds,
        "seer_claimed": seer_claimed,
        "doctor_publicly_identified": doctor_identified,
        "no_kill_nights": no_kill_nights,
        "total_holds": holds,
        "first_elimination_player": first_elim.get("player", "") if first_elim else "",
        "first_elimination_role": first_elim.get("role", "") if first_elim else "",
    }

rows = []

for fname in os.listdir(LOG_DIR):
    if not fname.endswith(".jsonl"):
        continue

    if fname.startswith("demo_llm_"):
        prompt_style = "strategic"
    elif fname.startswith("neutral_"):
        prompt_style = "neutral"
    else:
        continue

    row = process_file(os.path.join(LOG_DIR, fname), prompt_style)
    if row is not None:
        rows.append(row)

rows = [r for r in rows if r["winner"]]

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {OUT_CSV} with {len(rows)} completed games.")