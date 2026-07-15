#!/usr/bin/env python3
"""
Turniej strategii/agentów — twarde dane do weryfikacji hipotez.

Rozgrywa pojedynki 1 na 1 (round-robin) między wszystkimi wybranymi strategiami,
buduje macierz H2H (kto kogo ogrywa), ranking oraz rating Elo, a wyniki zapisuje
do CSV (do dalszej analizy w Excelu/pandas).

Użycie:
    python3 tournament.py                 # wszystkie strategie, 400 gier/parę
    python3 tournament.py 800             # 800 gier na parę
    python3 tournament.py 400 agresor kolejowy pomczerw rl   # wybrane
"""
import sys
import csv
from collections import defaultdict

from monopoly.engine import Game
from monopoly.strategies import ALL_STRATEGIES
import monopoly.agent  # rejestruje bazowe agenty przez import (jeśli używane)


def duel(a_key, b_key, games, max_rounds=250):
    """Pojedynek 1v1: zwraca liczbę wygranych a_key (naprzemienne pozycje startowe)."""
    a_wins = 0
    for g in range(games):
        a = ALL_STRATEGIES[a_key]()
        b = ALL_STRATEGIES[b_key]()
        if g % 2 == 0:
            spec = [("A", a), ("B", b)]
            a_idx = 0
        else:
            spec = [("B", b), ("A", a)]
            a_idx = 1
        res = Game(spec, seed=g * 100003 + 7, max_rounds=max_rounds).play()
        if res["winner"].index == a_idx:
            a_wins += 1
    return a_wins


def run(keys, games):
    n = len(keys)
    matrix = {k: {} for k in keys}
    elo = {k: 1500.0 for k in keys}
    avg_wr = defaultdict(float)

    print(f"Turniej 1v1 — {n} strategii, {games} gier/parę "
          f"({n*(n-1)//2} par)...\n")
    for i in range(n):
        for j in range(i + 1, n):
            a, b = keys[i], keys[j]
            aw = duel(a, b, games)
            wr_a = 100 * aw / games
            matrix[a][b] = wr_a
            matrix[b][a] = 100 - wr_a
            # Elo: przetwarzamy jako serię pojedynczych meczów (wynik zbiorczy)
            _update_elo(elo, a, b, aw, games - aw)
            print(f"  {a:<12} vs {b:<12}  {wr_a:5.1f}% : {100-wr_a:4.1f}%")

    for k in keys:
        vals = [matrix[k][o] for o in keys if o != k]
        avg_wr[k] = sum(vals) / max(1, len(vals))

    ranking = sorted(keys, key=lambda k: avg_wr[k], reverse=True)

    print(f"\n{'='*56}")
    print(" MACIERZ H2H (win% wiersza przeciw kolumnie)")
    print(f"{'='*56}")
    hdr = "".join(f"{k[:6]:>8}" for k in keys)
    print(f"{'':<12}{hdr}")
    for a in keys:
        row = "".join(f"{matrix[a].get(b, 0):>7.0f} " if b != a else f"{'—':>8}"
                      for b in keys)
        print(f"{a:<12}{row}")

    print(f"\n{'='*56}")
    print(" RANKING (średni win% H2H · Elo)")
    print(f"{'='*56}")
    for rank, k in enumerate(ranking, 1):
        bar = "█" * int(avg_wr[k] / 3)
        print(f"{rank:>2}. {k:<12} {avg_wr[k]:5.1f}%  Elo {elo[k]:4.0f}  {bar}")

    _export_csv(keys, matrix, avg_wr, elo)
    print(f"\nZapisano: tournament_h2h.csv, tournament_ranking.csv")
    return matrix, ranking, elo


def _update_elo(elo, a, b, a_wins, b_wins, K=8):
    """Aktualizuje Elo, PRZEPLATAJĄC wygrane/przegrane (bez biasu kolejności)."""
    i = j = 0
    while i < a_wins or j < b_wins:
        frac_a = i / a_wins if a_wins else 1.0
        frac_b = j / b_wins if b_wins else 1.0
        if i < a_wins and (frac_a <= frac_b or j >= b_wins):
            _elo_match(elo, a, b, 1.0, K); i += 1
        else:
            _elo_match(elo, a, b, 0.0, K); j += 1


def _elo_match(elo, a, b, score_a, K):
    ea = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
    elo[a] += K * (score_a - ea)
    elo[b] += K * ((1 - score_a) - (1 - ea))


def _export_csv(keys, matrix, avg_wr, elo):
    with open("tournament_h2h.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategia"] + keys)
        for a in keys:
            w.writerow([a] + [f"{matrix[a].get(b, '')}" if b != a else ""
                              for b in keys])
    with open("tournament_ranking.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategia", "sredni_winrate_H2H", "elo"])
        for k in sorted(keys, key=lambda k: avg_wr[k], reverse=True):
            w.writerow([k, round(avg_wr[k], 1), round(elo[k])])


if __name__ == "__main__":
    args = sys.argv[1:]
    games = 400
    keys = list(ALL_STRATEGIES.keys())
    if args and args[0].isdigit():
        games = int(args[0]); args = args[1:]
    if args:
        keys = args
        for k in keys:
            if k not in ALL_STRATEGIES:
                print(f"Nieznana strategia: {k}"); sys.exit(1)
    run(keys, games)
