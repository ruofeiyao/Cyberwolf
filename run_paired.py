import subprocess
import time

SEEDS = [
    6299577,
    7242578,
    1873482,
    8087954,
    2676392,
    887829,
    2184945,
    5983252,
    5199154,
    5682558,
    1200340,
    2283728,
]

for seed in SEEDS:
    print(f"\n===== seed={seed} | neutral =====")

    subprocess.run(
        [
            "python3",
            "run_demo.py",
            "--seed", str(seed),
            "--prompt_style", "neutral"
        ],
        check=True
    )

    print("sleeping...\n")
    time.sleep(10)