import json
from typing import Dict, Any, Optional
from schemas import ACTION_SCHEMA_HINT

GAME_RULES = """
Game Rules:
1. There are 8 players in total.
2. The default role setup is:
   - 2 Wolves
   - 1 Seer
   - 1 Doctor
   - 4 Villagers
3. The Villager side includes Villagers, the Seer, and the Doctor.
4. The Villager side wins if all Wolves are eliminated.
5. The Wolves win if the number of alive Wolves is equal to or greater than the number of alive non-Wolves.
6. The game proceeds in rounds.
7. Each round has the following stages:
   - NIGHT
   - DAY DISCUSSION
   - DAY VOTING

Night phase rules:
8. During NIGHT:
   - Wolves may choose one alive non-Wolf player to KILL, or choose HOLD.
   - The Seer may choose one alive player to INVESTIGATE, or choose HOLD.
   - The Doctor may choose one alive player to PROTECT, or choose HOLD.
   - Villagers have no night action.
9. If multiple Wolves choose different targets, the environment will resolve the final kill target.
10. If the Doctor protects the same player the Wolves target, that player survives.
11. If the Seer investigates a player, the Seer may receive private information about that player's role.
12. Private night results may be included in your private events.

Day discussion rules:
13. During DISCUSS, each alive player speaks once in public.
14. Discussion should use available shared evidence, such as:
   - who died in the night
   - prior vote history
   - prior holds
   - contradictions in public discussion
   - suspicious role claims
15. Players may claim roles, challenge claims, defend themselves, accuse others, or propose a voting direction.

Day voting rules:
16. During VOTE, each alive player may:
   - output action=VOTE with a valid alive target, or
   - output action=HOLD with target=null.
17. HOLD means you abstain because the evidence is not strong enough to justify a vote.
18. If enough votes reach the elimination threshold, that player is eliminated.
19. If no one reaches the threshold, no one is eliminated that round.

Reasoning constraints:
20. You should act strategically according to your private role and your win condition.
21. Do not explicitly reveal your private role in the reasoning field.
22. Do not say phrases like "As the Wolf", "As the Seer", "As the Doctor", or "As a Villager" in the reasoning field.
23. Use shared public evidence whenever possible.
24. Private information should guide your decision, but you should decide strategically whether to reveal or hide it in public discussion.
"""

ROLE_GUIDANCE = """
Role-specific guidance:

WOLF:
- Your objective is to help the wolf team survive and eliminate the villager side.
- During NIGHT, you may choose KILL or HOLD.
- During the day, you may accuse others, redirect suspicion, blend in, or strategically support or avoid votes.
- You may lie about your role.

SEER:
- Your objective is to help the villager side identify the Wolves.
- During NIGHT, you may choose INVESTIGATE or HOLD.
- If you receive investigation results in private events, you may decide whether to reveal them during discussion.
- Revealing too early may put you at risk.

DOCTOR:
- Your objective is to help the villager side survive.
- During NIGHT, you may choose PROTECT or HOLD.
- You may protect yourself if the environment allows it.
- You may decide whether to reveal your role during the day.

VILLAGER:
- Your objective is to help eliminate the Wolves.
- You have no special night action.
- You should use shared discussion, vote history, and public behavior to decide whom to suspect.
"""

NEUTRAL_STYLE_GUIDANCE = """
General guidance:
- Respond based on the current game state and the rules.
- Use the available information to produce a reasonable action.
- During discussion, you may share observations, respond to others, or ask questions.
- Do not assume hidden information beyond what is explicitly provided.
"""

def build_prompt(
    agent_id: str,
    role: str,
    obs: Dict[str, Any],
    instruction: Optional[str] = None,
    memory_block: Optional[str] = None,
    prompt_style = "strategic",
) -> str:
    state_json = json.dumps(
        {
            "round_id": obs["round_id"],
            "phase": obs["phase"],
            "alive": obs["alive"],
            "last_votes": obs.get("last_votes", {}),
            "last_holds": obs.get("last_holds", []),
            "public_events": obs.get("public_events", []),
            "public_history": obs.get("public_history", [])[-20:],
            "vote_threshold": obs.get("vote_threshold", 3),
            "private_events": obs.get("private_events", []),
            "wolf_teammates": obs.get("wolf_teammates", []),
        },
        ensure_ascii=False
    )

    parts = []
    parts.append(f"You are {agent_id} in an 8-player social deduction game.")
    parts.append(f"Your private role is: {role}.")
    parts.append("You MUST respond in English only.")
    parts.append("Never output Chinese.")
    parts.append("If you output Chinese, your answer is invalid.")

    if prompt_style == "strategic":
        parts.append("You must choose an action based on the game rules, the shared public state, the dialogue history, your private role, and any private events given to you.")
        parts.append("You are not a placeholder or random player.")
        parts.append("Your goal is to help your side win the game.")
        parts.append("Every discussion utterance should be strategically useful.")
        parts.append("Do not say generic things like 'I am not sure yet' unless uncertainty itself is strategically meaningful.")
        parts.append("Your reasoning and utterance should reflect the available evidence and your objective in the game.")
        parts.append(GAME_RULES)
        parts.append(ROLE_GUIDANCE)

    elif prompt_style == "neutral":
        parts.append("You must choose an action based on the game rules, the current public state, the dialogue history, your private role, and any private events given to you.")
        parts.append("Respond in a reasonable and coherent way based on the available information.")
        parts.append("During discussion, you may share observations, respond to others, or ask questions.")
        parts.append("Do not assume hidden information beyond what is explicitly provided.")
        parts.append(GAME_RULES)
        parts.append(NEUTRAL_STYLE_GUIDANCE)

    else:
        raise ValueError(f"Unknown prompt_style: {prompt_style}")

    if memory_block:
        parts.append(f"MEMORY:\n{memory_block}")

    if instruction:
        parts.append(f"PLAYER INSTRUCTION:\n{instruction}")

    public_events = obs.get("public_events", [])
    if public_events:
        parts.append("SHARED PUBLIC EVENTS:")
        for e in public_events:
            parts.append(f"- {e}")

    private_events = obs.get("private_events", [])
    if private_events:
        parts.append("PRIVATE EVENTS:")
        for e in private_events:
            parts.append(f"- {e}")

    wolf_teammates = obs.get("wolf_teammates", [])
    if wolf_teammates:
        parts.append("WOLF TEAMMATES:")
        for w in wolf_teammates:
            parts.append(f"- {w}")

    parts.append(f"PUBLIC STATE (JSON):\n{state_json}")

    parts.append("OUTPUT RULES (must follow):")
    parts.append("1) Output MUST be a single valid JSON object, and NOTHING else.")
    parts.append("2) Follow this JSON schema exactly:")
    parts.append(json.dumps(ACTION_SCHEMA_HINT, ensure_ascii=False))
    parts.append("3) The 'reasoning' field must be short and in English.")
    parts.append("4) The 'utterance' field must be natural English.")
    parts.append("5) In NIGHT:")
    parts.append("   - If you are a Wolf, output either action=KILL with a valid target or action=HOLD.")
    parts.append("   - If you are the Seer, output either action=INVESTIGATE with a valid target or action=HOLD.")
    parts.append("   - If you are the Doctor, output either action=PROTECT with a valid target or action=HOLD.")
    parts.append("   - If you are a Villager, do not invent a special night action.")
    parts.append("6) In DISCUSS, output action=SAY with a non-empty utterance.")
    parts.append("7) In VOTE, output either action=VOTE with a valid target or action=HOLD with target=null.")
    parts.append("8) Never leave utterance empty during DISCUSS.")
    parts.append("9) Do not explicitly reveal your hidden role in the reasoning field.")
    parts.append("10) Keep the JSON concise and valid.")
    parts.append("Return only the JSON object.")

    return "\n\n".join(parts)