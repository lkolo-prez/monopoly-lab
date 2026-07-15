#!/usr/bin/env python3
"""
Analiza planszy metodą Monte Carlo — dlaczego pewne pola są najlepsze.

1. Symuluje pojedynczy pionek wykonujący miliony rzutów wg pełnych zasad
   (dublety, 3 dublety -> więzienie, pola "idź do więzienia", karty Szansa
   i Kasa przemieszczające pionek). Zlicza częstotliwość lądowań.
2. Łączy częstotliwość z czynszem, by policzyć oczekiwany dochód
   i zwrot z inwestycji (ROI) dla każdej grupy kolorów.

Użycie: python3 analyze_board.py [liczba_rzutow]
"""
import sys
import random
from collections import defaultdict
from monopoly import data


def monte_carlo(steps=3_000_000, seed=1):
    rng = random.Random(seed)
    land = [0] * 40
    pos = 0
    in_jail = False
    doubles = 0
    # uproszczone talie kart wpływające na ruch
    chance_move = [c for c in data.CHANCE_CARDS if c[1] in
                   ("move_to", "advance_to", "move_back", "go_to_jail",
                    "nearest_rail", "nearest_util")]

    def nearest(p, targets):
        for s in range(1, 41):
            if (p + s) % 40 in targets:
                return (p + s) % 40
        return targets[0]

    for _ in range(steps):
        a, b = rng.randint(1, 6), rng.randint(1, 6)
        if in_jail:
            if a == b:
                in_jail = False
            else:
                land[data.POS_JAIL] += 1
                continue
            doubles = 0
        if a == b:
            doubles += 1
            if doubles == 3:
                pos = data.POS_JAIL
                in_jail = True
                doubles = 0
                land[pos] += 1
                continue
        else:
            doubles = 0
        pos = (pos + a + b) % 40
        typ = data.BOARD[pos][2]
        # pola i karty przenoszące pionek
        if typ == data.GOTO_JAIL:
            pos = data.POS_JAIL
            in_jail = True
        elif typ == data.CHANCE:
            desc, action, value = rng.choice(data.CHANCE_CARDS)
            if action in ("move_to", "advance_to"):
                pos = value
            elif action == "move_back":
                pos = (pos - value) % 40
            elif action == "go_to_jail":
                pos = data.POS_JAIL
                in_jail = True
            elif action == "nearest_rail":
                pos = nearest(pos, data.RAILROAD_POSITIONS)
            elif action == "nearest_util":
                pos = nearest(pos, data.UTILITY_POSITIONS)
        elif typ == data.CHEST:
            desc, action, value = rng.choice(data.CHEST_CARDS)
            if action == "move_to":
                pos = value
            elif action == "go_to_jail":
                pos = data.POS_JAIL
                in_jail = True
        land[pos] += 1
    return land


def report(land):
    total = sum(land)
    freq = [100 * x / total for x in land]

    print(f"\n{'='*70}")
    print(" TOP 15 NAJCZĘŚCIEJ ODWIEDZANYCH PÓL (Monte Carlo)")
    print(f"{'='*70}")
    order = sorted(range(40), key=lambda i: land[i], reverse=True)
    for rank, i in enumerate(order[:15], 1):
        name = data.BOARD[i][1]
        grp = data.BOARD[i][3] or ""
        length = int(freq[i] * 8)
        bar = "█" * min(length, 55) + ("»" if length > 55 else "")
        print(f"{rank:>2}. {name:<26}{freq[i]:>5.2f}%  {grp:<10}{bar}")

    # ROI per grupa: oczekiwany czynsz z hotelu / całkowity koszt (pola+domy)
    print(f"\n{'='*70}")
    print(" ROI GRUP KOLORÓW — dochód z hoteli vs koszt wejścia")
    print(f"{'='*70}")
    print(f"{'Grupa':<12}{'Koszt kompletu':>15}{'z hotelami':>13}"
          f"{'śr.czynsz/hotel':>16}{'ROI/kolejka':>13}")
    print("-" * 70)
    rows = []
    for group, positions in _groups().items():
        cost_props = sum(data.BOARD[p][4] for p in positions)
        hcost = data.BOARD[positions[0]][6]
        cost_hotels = cost_props + 5 * hcost * len(positions)   # 5 domów -> hotel
        # oczekiwany czynsz na jeden pełny obrót planszy (suma po polach)
        exp_rent = sum(freq[p] / 100 * data.BOARD[p][5][5] for p in positions)
        avg_hotel_rent = sum(data.BOARD[p][5][5] for p in positions) / len(positions)
        roi = exp_rent / cost_hotels * 100
        rows.append((roi, group, cost_hotels, avg_hotel_rent, exp_rent))
    rows.sort(reverse=True)
    names = {"orange": "pomarańcz.", "red": "czerwony", "lightblue": "jasnoniebie.",
             "pink": "różowy", "yellow": "żółty", "green": "zielony",
             "darkblue": "granatowy", "brown": "brązowy"}
    for roi, group, cost_hotels, avg_hotel_rent, exp_rent in rows:
        print(f"{names.get(group, group):<12}{cost_hotels:>15}"
              f"{'':>13}{avg_hotel_rent:>16.0f}{roi:>12.2f}%")
    print("-" * 70)
    print(" ROI/kolejka = oczekiwany czynsz za jeden pełny obieg planszy")
    print("               podzielony przez koszt kompletu z hotelami.")
    print("               Im wyżej, tym szybciej inwestycja się zwraca.\n")


def _groups():
    g = defaultdict(list)
    for pos, name, typ, group, *rest in data.BOARD:
        if typ == data.PROPERTY:
            g[group].append(pos)
    return g


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 3_000_000
    print(f"Symuluję {steps:,} rzutów...")
    land = monte_carlo(steps)
    report(land)
