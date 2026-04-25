import subprocess
import random
import time

PROMPT_STYLE = "neutral"
N_GAMES = 4

for i in range(N_GAMES):
    seed = random.randint(0, 10_000_000)
    print(f"\n===== GAME {i+1} | seed={seed} | style={PROMPT_STYLE} =====")

    subprocess.run(
        [
            "python3",
            "run_demo.py",
            "--seed", str(seed),
            "--prompt_style", PROMPT_STYLE
        ],
        check=True
    )

    print("Sleeping before next game...")
    time.sleep(10)