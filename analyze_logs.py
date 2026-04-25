import json
import glob
import os
import re
from collections import Counter, defaultdict

LOG_GLOB = "logs/*.jsonl"

def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def guess_prompt_style(path):
    name = os.path.basename(path).lower()
    if "neutral" in name:
        return "neutral"
    if "strategic" in name:
        return "strategic"
    return "unknown"

def reasoning_category(text):
    t = (text or "").lower()

    uncertainty_kw = [
        "not enough evidence", "insufficient evidence", "no strong evidence",
        "no clear suspect", "no clear suspects", "uncertain", "uncertainty",
        "ambiguous", "too early", "lack of evidence", "weak evidence",
        "no concrete leads", "no solid leads"
    ]
    risk_kw = [
        "risk", "risky", "eliminate the wrong", "wrong player", "mislynch",
        "mis-eliminate", "avoid eliminating", "could eliminate a fellow innocent",
        "prevent mislynches", "cautious"
    ]
    strategic_kw = [
        "probe", "probing", "observe", "wait", "gather more information",
        "capitaliz", "confusion", "pressure", "defensive", "strategic"
    ]

    if any(k in t for k in uncertainty_kw):
        return "uncertainty"
    if any(k in t for k in risk_kw):
        return "risk_avoidance"
    if any(k in t for k in strategic_kw):
        return "strategic"
    return "other"

def extract_suspects(text):
    if not text:
        return []
    return re.findall(r"\bP[0-7]\b", text)

def summarize_logs(paths):
    hold_by_role = Counter()
    vote_by_role = Counter()
    hold_by_role_prompt = defaultdict(Counter)
    reasoning_cat_all = Counter()
    reasoning_cat_by_role = defaultdict(Counter)

    no_elim_rounds = []
    successful_elim_rounds = []

    vote_history = defaultdict(list)
    suspect_history = defaultdict(list)

    for path in paths:
        rows = load_jsonl(path)
        prompt_style = guess_prompt_style(path)

        for r in rows:
            phase = r.get("phase")
            if phase == "VOTE" and "agent_id" in r:
                role = r.get("role_private", "UNKNOWN")
                agent = r["agent_id"]
                round_id = r["round_id"]
                action = r.get("action", {})
                reasoning = action.get("reasoning", "")
                act = action.get("action")

                if act == "HOLD":
                    hold_by_role[role] += 1
                    hold_by_role_prompt[prompt_style][role] += 1
                    cat = reasoning_category(reasoning)
                    reasoning_cat_all[cat] += 1
                    reasoning_cat_by_role[role][cat] += 1
                    vote_history[(path, agent)].append((round_id, "HOLD", reasoning))
                elif act == "VOTE":
                    vote_by_role[role] += 1
                    target = action.get("target")
                    vote_history[(path, agent)].append((round_id, target, reasoning))

                suspects = extract_suspects(reasoning)
                suspect_history[(path, agent)].append((round_id, suspects, reasoning))

            if phase == "VOTE_RESOLVE":
                ev = r.get("event", {})
                etype = ev.get("type")
                payload = ev.get("payload", {})
                if etype == "NO_ELIMINATION":
                    no_elim_rounds.append({
                        "file": os.path.basename(path),
                        "round": r.get("round_id"),
                        "payload": payload
                    })
                if etype == "ELIMINATION":
                    successful_elim_rounds.append({
                        "file": os.path.basename(path),
                        "round": r.get("round_id"),
                        "payload": payload
                    })

    vote_switches = []
    for key, hist in vote_history.items():
        hist = sorted(hist, key=lambda x: x[0])
        for i in range(1, len(hist)):
            prev_round, prev_target, prev_reason = hist[i-1]
            cur_round, cur_target, cur_reason = hist[i]
            if prev_target != cur_target:
                vote_switches.append({
                    "file": os.path.basename(key[0]),
                    "agent": key[1],
                    "from_round": prev_round,
                    "to_round": cur_round,
                    "from_action": prev_target,
                    "to_action": cur_target,
                    "from_reason": prev_reason,
                    "to_reason": cur_reason
                })

    suspect_switches = []
    for key, hist in suspect_history.items():
        hist = sorted(hist, key=lambda x: x[0])
        for i in range(1, len(hist)):
            prev_round, prev_suspects, prev_reason = hist[i-1]
            cur_round, cur_suspects, cur_reason = hist[i]
            prev_set, cur_set = set(prev_suspects), set(cur_suspects)
            if prev_set != cur_set and (prev_set or cur_set):
                suspect_switches.append({
                    "file": os.path.basename(key[0]),
                    "agent": key[1],
                    "from_round": prev_round,
                    "to_round": cur_round,
                    "from_suspects": sorted(prev_set),
                    "to_suspects": sorted(cur_set),
                    "from_reason": prev_reason,
                    "to_reason": cur_reason
                })

    return {
        "hold_by_role": hold_by_role,
        "vote_by_role": vote_by_role,
        "hold_by_role_prompt": hold_by_role_prompt,
        "reasoning_cat_all": reasoning_cat_all,
        "reasoning_cat_by_role": reasoning_cat_by_role,
        "no_elim_rounds": no_elim_rounds,
        "successful_elim_rounds": successful_elim_rounds,
        "vote_switches": vote_switches,
        "suspect_switches": suspect_switches,
    }

if __name__ == "__main__":
    paths = sorted(glob.glob(LOG_GLOB))
    print("FOUND FILES:", paths)

    out = summarize_logs(paths)

    print("\n=== HOLD by role ===")
    for role, n in out["hold_by_role"].most_common():
        print(role, n)

    print("\n=== VOTE by role ===")
    for role, n in out["vote_by_role"].most_common():
        print(role, n)

    print("\n=== HOLD by role and prompt ===")
    for prompt, ctr in out["hold_by_role_prompt"].items():
        print(f"\n[{prompt}]")
        for role, n in ctr.most_common():
            print(role, n)

    print("\n=== HOLD reasoning categories (all) ===")
    for cat, n in out["reasoning_cat_all"].most_common():
        print(cat, n)

    print("\n=== HOLD reasoning categories by role ===")
    for role, ctr in out["reasoning_cat_by_role"].items():
        print(f"\n[{role}]")
        for cat, n in ctr.most_common():
            print(cat, n)

    print("\n=== NO-ELIMINATION rounds ===")
    for x in out["no_elim_rounds"][:20]:
        print(x)

    print("\n=== SAMPLE vote switches (possible belief/action updates) ===")
    for x in out["vote_switches"][:15]:
        print("\nFILE:", x["file"], "AGENT:", x["agent"], f'R{x["from_round"]}->{x["to_round"]}')
        print("FROM ACTION:", x["from_action"])
        print("TO ACTION:", x["to_action"])
        print("FROM REASON:", x["from_reason"][:250])
        print("TO REASON:", x["to_reason"][:250])

    print("\n=== SAMPLE suspect switches (reasoning focus changed) ===")
    for x in out["suspect_switches"][:15]:
        print("\nFILE:", x["file"], "AGENT:", x["agent"], f'R{x["from_round"]}->{x["to_round"]}')
        print("FROM SUSPECTS:", x["from_suspects"])
        print("TO SUSPECTS:", x["to_suspects"])
        print("FROM REASON:", x["from_reason"][:250])
        print("TO REASON:", x["to_reason"][:250])
