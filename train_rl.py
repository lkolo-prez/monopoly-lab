#!/usr/bin/env python3
"""
Trener RL: uczy politykę zakupu metodą REINFORCE, zapisuje wagi i drukuje
je w formacie gotowym do wklejenia do silnika przeglądarkowego (JS).

Użycie:
    python3 train_rl.py                 # 8000 epizodów
    python3 train_rl.py 15000           # dłuższy trening
"""
import sys
import json
from monopoly import rl


def main():
    episodes = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Trening RL (REINFORCE) — {episodes} epizodów self-play...\n")
    w, curve = rl.train(episodes=episodes, n_players=4, eval_every=max(500, episodes // 8))

    # zapis wag
    with open("monopoly/rl_policy.json", "w") as f:
        json.dump({"weights": w, "features": rl.NF, "curve": curve}, f, indent=2)

    print("\nWyuczone wagi (cechy: bias, afford, completes, advances, tier, is_rail,")
    print("               is_util, landing, cash_share, phase, buffer, n_players):")
    print("  [" + ", ".join(f"{x:.4f}" for x in w) + "]")
    print("\nZapisano do monopoly/rl_policy.json")
    print("\nWklej do engine.core.js jako RL_WEIGHTS:")
    print("const RL_WEIGHTS = [" + ",".join(f"{x:.4f}" for x in w) + "];")


if __name__ == "__main__":
    main()
