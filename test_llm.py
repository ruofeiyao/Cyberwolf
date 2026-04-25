from agents.llm_agent import LlmAgent

obs = {
    "round_id": 1,
    "phase": "DISCUSS",
    "alive": {"P0": True, "P1": True, "P2": True, "P3": True, "P4": True},
    "last_votes": {},
    "public_history": []
}

agent = LlmAgent(
    agent_id="P0",
    model="qwen2.5:7b-instruct",
    role="VILLAGER",
    temperature=0.3,
    memory_on=False,
    reflection_on=False
)

action = agent.act(obs)
print(action)