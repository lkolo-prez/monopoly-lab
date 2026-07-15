#!/usr/bin/env python3
"""
Tryby SZYBKIE z NEW MONOPOLY (Ubisoft, PS5) — która strategia wygrywa w każdym celu.

Cele trybu Szybkiego (wygrywa pierwszy, kto go osiągnie):
  • real_estate  (Real Estate Agent) — pierwszy z N nieruchomościami
  • magnate      (Magnate)           — pierwszy z 1800 gotówki
  • architect    (Architect)         — dom na każdym polu pełnego kompletu
  • hotel_manager(Hotel Manager)     — pierwszy hotel
  • town_planner (Town Planner)      — N pełnych kompletów
  • landowner    (Landowner)         — zebrać N czynszu

Symuluje wszystkie 7 strategii z uczciwą rotacją i pokazuje, która najczęściej
osiąga cel jako pierwsza — czyli najlepszą strategię pod dany tryb.

Użycie:
    python3 run_modes.py            # 4 graczy, 2000 gier na cel
    python3 run_modes.py 5000       # więcej gier
    python3 run_modes.py 2000 6     # 6 graczy
"""
import sys
import time
from collections import defaultdict

from monopoly import Game
from monopoly.strategies import ALL_STRATEGIES

ROSTER = list(ALL_STRATEGIES.keys())
NAME2KEY = {ALL_STRATEGIES[k]().name: k for k in ROSTER}
KEYNAME = {k: ALL_STRATEGIES[k]().name for k in ROSTER}
R = len(ROSTER)

GOALS = [
    ("Real Estate Agent", "Pierwszy z 6 nieruchomościami",
     {"type": "real_estate", "target": 6}),
    ("Magnate", "Pierwszy z 1800 gotówki",
     {"type": "magnate", "target": 1800}),
    ("Town Planner", "Pierwszy z 2 pełnymi kompletami",
     {"type": "town_planner", "target": 2}),
    ("Architect", "Pierwszy z domem na całym komplecie",
     {"type": "architect", "target": 1}),
    ("Hotel Manager", "Pierwszy hotel",
     {"type": "hotel_manager", "target": 1}),
    ("Landowner", "Pierwszy z 500 zebranego czynszu",
     {"type": "landowner", "target": 500}),
]


def run_goal(goal, n_players, games, max_rounds=250):
    wins = defaultdict(int)
    played = defaultdict(int)
    reached = 0
    rounds_to_goal = 0
    for g in range(games):
        start = g % R
        keys = [ROSTER[(start + i) % R] for i in range(n_players)]
        players = [(KEYNAME[k], ALL_STRATEGIES[k]()) for k in keys]
        game = Game(players, seed=g, max_rounds=max_rounds, goal=goal)
        res = game.play()
        for k in keys:
            played[k] += 1
        wins[NAME2KEY[res["winner_strategy"]]] += 1
        if res.get("goal_reached"):
            reached += 1
            rounds_to_goal += res["rounds"]
    return wins, played, reached, rounds_to_goal, games


def print_goal(title, desc, stats, n_players):
    wins, played, reached, rounds_to_goal, games = stats
    base = 100 / n_players
    print(f"\n  ▶ {title} — {desc}")
    print(f"  {'-'*60}")
    rows = sorted(
        ((100 * wins[k] / played[k] if played[k] else 0, k) for k in ROSTER),
        reverse=True)
    for wr, k in rows:
        delta = wr - base
        mark = "▲" if delta > 2 else ("▼" if delta < -2 else " ")
        print(f"  {KEYNAME[k]:<16}{wr:>6.1f}%   (baza {base:.0f}%, {delta:+.1f}{mark})")
    avg = rounds_to_goal / reached if reached else 0
    print(f"  {'-'*60}")
    print(f"  cel osiągnięty w {100*reached/games:.0f}% gier, "
          f"średnio po {avg:.0f} rundach → NAJLEPSZA: {KEYNAME[rows[0][1]]}")
    return rows[0][1]


if __name__ == "__main__":
    args = sys.argv[1:]
    games = 2000
    n_players = 4
    if len(args) >= 1 and args[0].isdigit():
        games = int(args[0])
    if len(args) >= 2 and args[1].isdigit():
        n_players = int(args[1])

    print("=" * 64)
    print(f" TRYBY SZYBKIE NEW MONOPOLY — {n_players} graczy, {games} gier/cel")
    print(" Która strategia najczęściej osiąga cel jako pierwsza?")
    print("=" * 64)
    t0 = time.time()
    best = {}
    for title, desc, goal in GOALS:
        stats = run_goal(goal, n_players, games)
        best[title] = print_goal(title, desc, stats, n_players)

    print("\n" + "=" * 64)
    print(" PODSUMOWANIE — najlepsza strategia pod każdy cel trybu Szybkiego")
    print("=" * 64)
    for title, _, _ in GOALS:
        print(f"  {title:<20} → {KEYNAME[best[title]]}")
    print(f"\n(czas: {time.time()-t0:.0f}s)")
