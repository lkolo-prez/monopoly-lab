#!/usr/bin/env python3
"""
Pełny przebieg jednej gry — tura po turze, w bardzo szybkim tempie.

Użycie:
    python3 run_game.py                 # domyślna 4-osobowa gra
    python3 run_game.py 42              # z ziarnem losowości 42 (powtarzalna)
    python3 run_game.py 42 agresor pomczerw ostrozny kolejowy
"""
import sys
from monopoly import Game
from monopoly.strategies import ALL_STRATEGIES


def main():
    args = sys.argv[1:]
    seed = 7
    keys = ["agresor", "pomczerw", "ostrozny", "kolejowy"]
    if args and args[0].lstrip("-").isdigit():
        seed = int(args[0])
        args = args[1:]
    if args:
        keys = args

    players = []
    used = {}
    for k in keys:
        cls = ALL_STRATEGIES[k]
        used[k] = used.get(k, 0) + 1
        label = cls().name + (f"-{used[k]}" if keys.count(k) > 1 else "")
        players.append((label, cls()))

    lines = []
    game = Game(players, seed=seed, logger=lambda *a: lines.append(" ".join(map(str, a))),
                max_rounds=400)
    res = game.play()

    print("\n".join(lines))
    print("\n" + "=" * 60)
    print(f" KONIEC GRY — ziarno {seed}, {res['rounds']} rund"
          + (" (nokaut)" if res["finished"] else " (limit rund)"))
    print("=" * 60)
    print(f" ZWYCIĘZCA: {res['winner'].name} [{res['winner_strategy']}]\n")
    print(f" {'Miejsce':<8}{'Gracz':<26}{'Majątek netto':>14}{'Status':>12}")
    print(" " + "-" * 58)
    for i, (name, strat, worth, bankrupt) in enumerate(res["ranking"], 1):
        status = "BANKRUT" if bankrupt else "w grze"
        print(f" {i:<8}{name:<26}{worth:>14}{status:>12}")


if __name__ == "__main__":
    main()
