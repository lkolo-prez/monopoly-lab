#!/usr/bin/env python3
"""
Trener ewolucyjny (CEM) — wypracowuje najlepszy schemat gry (własny model Monopoly).

Uruchom wielokrotnie — każdy start WZNAWIA trening od zapisanego mistrza,
więc możesz doskonalić model "bez końca".

Użycie:
    python3 train_evolve.py                 # 20 pokoleń
    python3 train_evolve.py 50              # 50 pokoleń
    python3 train_evolve.py 50 6           # 50 pokoleń, gry 6-osobowe
"""
import sys
from monopoly import evolve


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    players = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    print(f"Ewolucja CEM — {gens} pokoleń, gry {players}-osobowe, panel: "
          f"{', '.join(evolve.PANEL)}\n")
    genome, fit, curve = evolve.cem(generations=gens, players=players)

    print(f"\nNajlepszy mistrz: +{fit:.1f} pkt% przewagi nad bazą (średnio po panelach)")
    print("Wagi grup wytrenowanego modelu:")
    for i, k in enumerate(evolve.KEYS):
        print(f"  {k:<11} {genome[i]:.2f}")
    print(f"  rezerwa      {genome[len(evolve.KEYS)]:.0f}$")
    print(f"  max_domy     {genome[len(evolve.KEYS)+1]:.1f}")
    print(f"  próg_więz.   {genome[len(evolve.KEYS)+2]:.0f} rundy")
    print(f"\nZapisano model: monopoly/evolved_champion.json")
    print("Dostępny wszędzie jako strategia 'champion' (po ponownym imporcie).")


if __name__ == "__main__":
    main()
