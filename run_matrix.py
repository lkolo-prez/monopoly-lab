#!/usr/bin/env python3
"""
Matryca wariantów: symuluje wiele konfiguracji Monopoly i porównuje strategie.

Osie badania:
  • liczba graczy: 2, 3, 4, 5, 6
  • kapitał startowy: 1500 oraz 2000
  • przymusowe licytacje: włączone / wyłączone
  • handel (wymiany): włączony / wyłączony
  • hipoteki: włączone / wyłączone

Wszystkie 7 strategii jest sprawiedliwie rotowanych po stołach (każda gra co
najwyżej N krzeseł, ale w tysiącach gier każda strategia zasiada tyle samo razy
i na każdej pozycji), więc % wygranych jest porównywalny mimo różnej liczby graczy.

Użycie:
    python3 run_matrix.py                 # pełna matryca, 1500 gier/konfig
    python3 run_matrix.py 500             # szybciej, 500 gier/konfig
    python3 run_matrix.py 3000 A          # tylko STUDIUM A (graczy x kapitał)
    python3 run_matrix.py 3000 B          # tylko STUDIUM B (warianty zasad)
"""
import sys
import time
from collections import defaultdict

from monopoly import Game
from monopoly.strategies import ALL_STRATEGIES

ROSTER = list(ALL_STRATEGIES.keys())            # 7 strategii
NAME2KEY = {ALL_STRATEGIES[k]().name: k for k in ROSTER}
KEYNAME = {k: ALL_STRATEGIES[k]().name for k in ROSTER}
R = len(ROSTER)


def run_config(n_players, games, start_cash=1500, forced_auction=True,
               allow_trades=True, allow_mortgage=True, max_rounds=400):
    wins = defaultdict(int)
    played = defaultdict(int)
    net_sum = defaultdict(float)
    bankr = defaultdict(int)
    total_rounds = 0
    finished = 0

    for g in range(games):
        start = g % R
        keys = [ROSTER[(start + i) % R] for i in range(n_players)]
        players = [(KEYNAME[k], ALL_STRATEGIES[k]()) for k in keys]
        game = Game(players, seed=g, max_rounds=max_rounds, start_cash=start_cash,
                    forced_auction=forced_auction, allow_trades=allow_trades,
                    allow_mortgage=allow_mortgage)
        res = game.play()
        for k in keys:
            played[k] += 1
        wins[NAME2KEY[res["winner_strategy"]]] += 1
        total_rounds += res["rounds"]
        if res["finished"]:
            finished += 1
        for name, strat_name, worth, is_bankrupt in res["ranking"]:
            k = NAME2KEY[strat_name]
            net_sum[k] += worth
            if is_bankrupt:
                bankr[k] += 1
    return {
        "wins": wins, "played": played, "net_sum": net_sum, "bankr": bankr,
        "rounds": total_rounds, "finished": finished, "games": games,
        "n_players": n_players,
    }


def print_config(title, stats):
    n = stats["n_players"]
    games = stats["games"]
    base = 100 / n
    avg_rounds = stats["rounds"] / games
    fin = 100 * stats["finished"] / games
    print(f"\n  {title}")
    print(f"  {'-'*62}")
    print(f"  {'strategia':<16}{'grała':>7}{'wygrane':>9}{'% wygr.':>9}"
          f"{'vs baza':>9}{'śr.majątek':>12}")
    rows = []
    for k in ROSTER:
        pl = stats["played"][k]
        w = stats["wins"][k]
        wr = 100 * w / pl if pl else 0
        net = stats["net_sum"][k] / pl if pl else 0
        rows.append((wr, k, pl, w, net))
    rows.sort(reverse=True)
    for wr, k, pl, w, net in rows:
        delta = wr - base
        mark = "▲" if delta > 1.5 else ("▼" if delta < -1.5 else " ")
        print(f"  {KEYNAME[k]:<16}{pl:>7}{w:>9}{wr:>8.1f}%"
              f"{delta:>+8.1f}{mark}{net:>11.0f}")
    print(f"  {'-'*62}")
    print(f"  baza losowa {base:.1f}% | śr. długość {avg_rounds:.0f} rund | "
          f"nokaut w {fin:.0f}% gier")
    best = rows[0]
    return best[1]                      # klucz najlepszej strategii


def study_a(games):
    print("\n" + "=" * 66)
    print(" STUDIUM A — liczba graczy (2-6) × kapitał startowy (1500 / 2000)")
    print(" (przymusowe licytacje, handel i hipoteki: WŁĄCZONE)")
    print("=" * 66)
    grid = {}
    for cash in (1500, 2000):
        for n in range(2, 7):
            stats = run_config(n, games, start_cash=cash)
            best = print_config(f"{n} graczy, start {cash}", stats)
            grid[(n, cash)] = best
    print("\n" + "=" * 66)
    print(" PODSUMOWANIE STUDIUM A — najlepsza strategia w każdym wariancie")
    print("=" * 66)
    print(f" {'graczy':<8}{'kapitał 1500':<22}{'kapitał 2000':<22}")
    print(" " + "-" * 50)
    for n in range(2, 7):
        print(f" {n:<8}{KEYNAME[grid[(n,1500)]]:<22}{KEYNAME[grid[(n,2000)]]:<22}")


def study_b(games):
    print("\n" + "=" * 66)
    print(" STUDIUM B — wpływ mechanik (4 graczy, kapitał 1500)")
    print("=" * 66)
    variants = [
        ("Wszystko WŁĄCZONE (baza)", dict()),
        ("BEZ przymusowych licytacji", dict(forced_auction=False)),
        ("BEZ handlu (wymian)", dict(allow_trades=False)),
        ("BEZ hipotek", dict(allow_mortgage=False)),
        ("BEZ handlu i BEZ hipotek", dict(allow_trades=False, allow_mortgage=False)),
    ]
    for title, kw in variants:
        stats = run_config(4, games, start_cash=1500, **kw)
        print_config(title, stats)


if __name__ == "__main__":
    args = sys.argv[1:]
    games = 1500
    which = "AB"
    if args and args[0].isdigit():
        games = int(args[0])
        args = args[1:]
    if args:
        which = args[0].upper()

    t0 = time.time()
    if "A" in which:
        study_a(games)
    if "B" in which:
        study_b(games)
    print(f"\n(Łączny czas: {time.time()-t0:.0f}s, {games} gier na konfigurację)")
