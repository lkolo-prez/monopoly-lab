#!/usr/bin/env python3
"""
Masowa symulacja: rozgrywa tysiące szybkich gier i porównuje strategie.

Użycie:
    python3 run_sim.py                  # 5000 gier, wszystkie 5 strategii
    python3 run_sim.py 20000            # 20000 gier
    python3 run_sim.py 5000 agresor pomczerw ostrozny   # wybrane strategie
"""
import sys
import time
from collections import defaultdict

from monopoly import Game
from monopoly.strategies import ALL_STRATEGIES


def build_players(strategy_keys):
    return [(ALL_STRATEGIES[k]().name, ALL_STRATEGIES[k]()) for k in strategy_keys]


def run(n_games, strategy_keys, max_rounds=400):
    wins = defaultdict(int)
    finishes = defaultdict(int)          # gry zakończone bankructwem reszty
    net_sum = defaultdict(float)
    net_count = defaultdict(int)
    bankruptcies = defaultdict(int)
    total_rounds = 0
    finished_games = 0

    # rotujemy kolejność startową, by nie faworyzować pierwszego gracza
    base = list(strategy_keys)
    t0 = time.time()
    for g in range(n_games):
        order = base[g % len(base):] + base[:g % len(base)]
        players = build_players(order)
        game = Game(players, seed=g, max_rounds=max_rounds)
        res = game.play()
        wins[res["winner_strategy"]] += 1
        if res["finished"]:
            finished_games += 1
            finishes[res["winner_strategy"]] += 1
        total_rounds += res["rounds"]
        for name, strat, worth, bankrupt in res["ranking"]:
            net_sum[strat] += worth
            net_count[strat] += 1
            if bankrupt:
                bankruptcies[strat] += 1
    dt = time.time() - t0

    print(f"\n{'='*66}")
    print(f" WYNIKI SYMULACJI — {n_games} gier  ({dt:.1f}s, "
          f"{n_games/dt:.0f} gier/s)")
    print(f" Strategie: {', '.join(strategy_keys)}")
    print(f" Gry rozstrzygnięte przez bankructwo: {finished_games} "
          f"({100*finished_games/n_games:.0f}%), "
          f"średnia długość: {total_rounds/n_games:.0f} rund")
    print(f"{'='*66}")
    print(f"{'Strategia':<24}{'Wygrane':>9}{'% wygr.':>9}"
          f"{'śr. majątek':>14}{'% bankr.':>10}")
    print(f"{'-'*66}")
    ranking = sorted(wins.items(), key=lambda x: x[1], reverse=True)
    for strat, w in ranking:
        avg_net = net_sum[strat] / max(1, net_count[strat])
        bankr = 100 * bankruptcies[strat] / max(1, net_count[strat])
        print(f"{strat:<24}{w:>9}{100*w/n_games:>8.1f}%"
              f"{avg_net:>14.0f}{bankr:>9.1f}%")
    print(f"{'='*66}")
    baseline = 100 / len(strategy_keys)
    print(f" (Baza losowa = {baseline:.1f}% wygranych na strategię)")
    return wins


if __name__ == "__main__":
    args = sys.argv[1:]
    n = 5000
    keys = list(ALL_STRATEGIES.keys())
    if args and args[0].isdigit():
        n = int(args[0])
        args = args[1:]
    if args:
        keys = args
        for k in keys:
            if k not in ALL_STRATEGIES:
                print(f"Nieznana strategia: {k}. Dostępne: "
                      f"{', '.join(ALL_STRATEGIES)}")
                sys.exit(1)
    run(n, keys)
