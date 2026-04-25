import pandas as pd

df = pd.read_csv("game_summary_labeled.csv")

# 删掉不属于paired实验的 seed=42
df = df[df["seed"] != 42]

# 每个 seed 每个 style 只保留一条
df = df.drop_duplicates(subset=["seed", "prompt_style"], keep="first")

s = df[df["prompt_style"] == "strategic"].copy()
n = df[df["prompt_style"] == "neutral"].copy()

paired = pd.merge(s, n, on="seed", suffixes=("_s", "_n"))

paired["winner_flip"] = paired["winner_s"] != paired["winner_n"]
paired["holds_diff"] = paired["total_holds_n"] - paired["total_holds_s"]
paired["rounds_diff"] = paired["rounds_n"] - paired["rounds_s"]
paired["no_kill_diff"] = paired["no_kill_nights_n"] - paired["no_kill_nights_s"]

paired.to_csv("paired_summary.csv", index=False)

print(paired[[
    "seed",
    "winner_s",
    "winner_n",
    "winner_flip",
    "total_holds_s",
    "total_holds_n",
    "rounds_s",
    "rounds_n",
    "no_kill_nights_s",
    "no_kill_nights_n"
]])
print()
print("paired seeds:", len(paired))
print("winner flips:", int(paired["winner_flip"].sum()))
print("avg holds strategic:", paired["total_holds_s"].mean())
print("avg holds neutral:", paired["total_holds_n"].mean())
print("avg rounds strategic:", paired["rounds_s"].mean())
print("avg rounds neutral:", paired["rounds_n"].mean())
print("avg no-kill strategic:", paired["no_kill_nights_s"].mean())
print("avg no-kill neutral:", paired["no_kill_nights_n"].mean())